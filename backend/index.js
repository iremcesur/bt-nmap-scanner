const express = require('express');
const cors = require('cors');
const app = express();
const advancedNmapRoute = require('./routes/advanced_nmap');
const discoverRoute = require('./routes/discover');
const feedbackRoute = require('./routes/feedback');
const behavioralScanRoute = require('./routes/behavioral_scan');

app.use(cors());
app.use(express.json());

// Routes
app.use('/api/advanced_nmap', advancedNmapRoute);
app.use('/api/discover', discoverRoute);
app.use('/api/feedback', feedbackRoute);
app.use('/api/behavioral_scan', behavioralScanRoute);

const PORT = 4001;
app.listen(PORT, () => {
    console.log(`BT Nmap Scanner Backend listening on port ${PORT}`);
});
