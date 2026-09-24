const router = require("express").Router();
const { spawn } = require('child_process');
const path = require('path');

// Katman 3 "Derin Davranışsal Tarama" - streams live measurements over Server-Sent
// Events instead of the single buffered JSON response the other routes use, since a
// behavioral scan runs for tens of seconds. The Python side (advanced_nmap_scanner.py
// --behavioral) prints one JSON object per stdout line as each event happens; this
// route reads stdout line by line and relays each line as an SSE `data:` event as
// soon as it arrives.
router.get('/:macAddress', (req, res) => {
    const macAddress = req.params.macAddress;
    const duration = parseInt(req.query.duration, 10);
    const interval = parseInt(req.query.interval, 10);
    const durationSeconds = Number.isFinite(duration) && duration > 0 ? duration : 45;
    const sampleIntervalSeconds = Number.isFinite(interval) && interval > 0 ? interval : 2;
    const isBle = req.query.ble === 'true';

    const pythonScriptPath = path.join(__dirname, 'pythonfiles/advanced_nmap_scanner.py');
    const args = [pythonScriptPath, '--behavioral', macAddress, String(durationSeconds), String(sampleIntervalSeconds)];
    if (isBle) args.push('--ble');

    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
    });
    res.flushHeaders();

    const pythonProcess = spawn('python3', args);
    let stdoutBuffer = '';

    const sendEvent = (obj) => {
        if (res.writableEnded) return;
        res.write(`data: ${JSON.stringify(obj)}\n\n`);
    };

    pythonProcess.stdout.on('data', (chunk) => {
        stdoutBuffer += chunk.toString();
        const lines = stdoutBuffer.split('\n');
        stdoutBuffer = lines.pop(); // last element may be a partial line - keep it buffered
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            try {
                sendEvent(JSON.parse(trimmed));
            } catch (e) {
                // Every stdout line from --behavioral mode is supposed to be JSON;
                // surface anything that isn't rather than silently dropping it.
                sendEvent({ type: 'status', message: trimmed });
            }
        }
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[behavioral_scan ${macAddress}] ${data.toString().trim()}`);
    });

    pythonProcess.on('close', () => {
        const trailing = stdoutBuffer.trim();
        if (trailing) {
            try { sendEvent(JSON.parse(trailing)); } catch (e) { /* incomplete trailing line, nothing to salvage */ }
        }
        if (!res.writableEnded) res.end();
    });

    pythonProcess.on('error', (err) => {
        sendEvent({ type: 'error', message: err.message });
        if (!res.writableEnded) res.end();
    });

    // Client cancelled/disconnected - don't just kill -9 the child. SIGTERM lets
    // Python's handler (_install_sigterm_handler in advanced_nmap_scanner.py) exit
    // its sampling loop gracefully and still compute/emit a "complete" summary from
    // whatever it collected so far (useful for server-side logs even though the HTTP
    // response itself is already gone at that point).
    req.on('close', () => {
        if (!pythonProcess.killed) {
            pythonProcess.kill('SIGTERM');
        }
    });
});

module.exports = router;
