const router = require("express").Router();
const { spawn } = require('child_process');
const path = require('path');

router.post('/', (req, res) => {
    const { mac, timestamp, is_correct, actual_value, notes } = req.body;

    if (!mac || !timestamp || typeof is_correct !== 'boolean') {
        return res.status(400).json({ error: 'mac, timestamp and is_correct (boolean) are required' });
    }

    const pythonScriptPath = path.join(__dirname, 'pythonfiles/record_feedback.py');
    const payload = JSON.stringify({ mac, timestamp, is_correct, actual_value, notes });
    const pythonProcess = spawn('python3', [pythonScriptPath, payload]);

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error('Feedback stderr chunk:', data.toString());
    });

    pythonProcess.on('close', (code) => {
        try {
            const parsed = JSON.parse(output.trim());
            if (code !== 0 || parsed.error) {
                return res.status(code !== 0 ? 500 : 404).json(parsed);
            }
            res.json(parsed);
        } catch (e) {
            console.error('Error parsing feedback output:', e);
            console.error('Raw Output:', output, errorOutput);
            res.status(500).json({ error: 'Failed to record feedback', raw: output });
        }
    });
});

module.exports = router;
