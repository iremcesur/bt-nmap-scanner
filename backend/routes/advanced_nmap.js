const router = require("express").Router();
const { spawn } = require('child_process');
const path = require('path');

router.get('/:macAddress', (req, res) => {
    const macAddress = req.params.macAddress;
    const pythonScriptPath = path.join(__dirname, 'pythonfiles/advanced_nmap_scanner.py');
    // Only write a research_evaluation.csv row when the caller has said they
    // can actually verify this device's ground truth - defaults to "false" on
    // any missing/unexpected value, same fail-safe direction as the Python
    // side's own default (see advanced_nmap_scanner.py's log_ground_truth).
    const logGroundTruth = req.query.logGroundTruth === 'true' ? 'true' : 'false';

    const pythonProcess = spawn('python3', [pythonScriptPath, macAddress, logGroundTruth]);

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error('Python stderr chunk:', data.toString());
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error('Scanner process exited with code:', code);
            console.error(errorOutput);
            return res.status(500).json({ error: 'Internal server error', details: errorOutput });
        }
        try {
            // Find the JSON block in the python output (it might print progress text before)
            const jsonStartIndex = output.indexOf('{');
            const jsonEndIndex = output.lastIndexOf('}') + 1;
            
            if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
                const jsonStr = output.substring(jsonStartIndex, jsonEndIndex);
                const parsedData = JSON.parse(jsonStr);
                
                // We also want to include the raw terminal logs up to the JSON
                const rawLogs = output.substring(0, jsonStartIndex).trim();
                parsedData.raw_logs = rawLogs;
                
                res.json(parsedData);
            } else {
                throw new Error("No JSON found in Python output");
            }
        } catch (e) {
            console.error("Error parsing Python JSON output:", e);
            console.error("Raw Output:", output);
            res.status(500).json({ error: 'Failed to parse scanner output', raw: output });
        }
    });
});

module.exports = router;
