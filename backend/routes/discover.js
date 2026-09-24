const router = require("express").Router();
const { spawn } = require('child_process');
const path = require('path');

router.get('/', (req, res) => {
    const pythonScriptPath = path.join(__dirname, 'pythonfiles/discover_devices.py');
    const pythonProcess = spawn('python3', [pythonScriptPath]);

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error('Discovery stderr chunk:', data.toString());
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error('Discovery process exited with code:', code);
            console.error(errorOutput);
            return res.status(500).json({ error: 'Discovery failed', details: errorOutput });
        }
        try {
            const jsonStartIndex = output.indexOf('{');
            const jsonEndIndex = output.lastIndexOf('}') + 1;

            if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
                const jsonStr = output.substring(jsonStartIndex, jsonEndIndex);
                const parsedData = JSON.parse(jsonStr);
                res.json(parsedData);
            } else {
                throw new Error("No JSON found in Python output");
            }
        } catch (e) {
            console.error("Error parsing discovery JSON output:", e);
            console.error("Raw Output:", output);
            res.status(500).json({ error: 'Failed to parse discovery output', raw: output });
        }
    });
});

module.exports = router;
