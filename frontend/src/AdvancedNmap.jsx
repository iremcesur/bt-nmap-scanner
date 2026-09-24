import React, { useState } from 'react';

const SUPPORT_BADGES = {
    classic: { label: 'Classic BR/EDR — Full Fingerprint Support', color: '#155724', backgroundColor: '#d4edda' },
    ble: { label: 'BLE — Limited/Experimental Support', color: '#856404', backgroundColor: '#fff3cd' },
    unknown: { label: 'Unknown', color: '#495057', backgroundColor: '#e2e3e5' },
};

const SupportBadge = ({ supportLevel, deviceType }) => {
    const badge = SUPPORT_BADGES[deviceType] || SUPPORT_BADGES.unknown;
    return (
        <span style={{
            fontSize: '11px',
            fontWeight: 'bold',
            padding: '3px 8px',
            borderRadius: '10px',
            color: badge.color,
            backgroundColor: badge.backgroundColor,
            whiteSpace: 'nowrap',
        }}>
            {badge.label}
        </span>
    );
};

const AdvancedNmap = () => {
    const [mac, setMac] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    // Unchecked by default: most scans (a public sweep of strangers' devices)
    // can never be verified, and logging them anyway would leave
    // research_evaluation.csv full of permanently-blank rows indistinguishable
    // from real ground-truth entries. Only check this for a device you can
    // actually confirm the true OS/type of afterwards.
    const [canVerify, setCanVerify] = useState(false);

    const [devices, setDevices] = useState([]);
    const [discovering, setDiscovering] = useState(false);
    const [discoverError, setDiscoverError] = useState(null);

    const [feedbackChoice, setFeedbackChoice] = useState(null);
    const [actualValue, setActualValue] = useState('');
    const [feedbackNotes, setFeedbackNotes] = useState('');
    const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
    const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
    const [feedbackError, setFeedbackError] = useState(null);

    const resetFeedback = () => {
        setFeedbackChoice(null);
        setActualValue('');
        setFeedbackNotes('');
        setFeedbackSubmitting(false);
        setFeedbackSubmitted(false);
        setFeedbackError(null);
    };

    const submitFeedback = async (isCorrect) => {
        setFeedbackSubmitting(true);
        setFeedbackError(null);

        try {
            const response = await fetch('http://localhost:4001/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mac: result.features.mac,
                    timestamp: result.timestamp,
                    is_correct: isCorrect,
                    actual_value: actualValue,
                    notes: feedbackNotes,
                }),
            });
            const data = await response.json();

            if (response.ok) {
                setFeedbackSubmitted(true);
            } else {
                setFeedbackError(data.error || 'Failed to submit feedback');
            }
        } catch (err) {
            setFeedbackError(err.message);
        } finally {
            setFeedbackSubmitting(false);
        }
    };

    const handleDiscover = async () => {
        setDiscovering(true);
        setDiscoverError(null);
        setDevices([]);

        try {
            const response = await fetch('http://localhost:4001/api/discover');
            const data = await response.json();

            if (response.ok) {
                setDevices(data.devices || []);
            } else {
                setDiscoverError(data.error || 'Discovery failed');
            }
        } catch (err) {
            setDiscoverError(err.message);
        } finally {
            setDiscovering(false);
        }
    };

    const selectedDevice = devices.find((d) => d.mac === mac);

    const handleScan = async () => {
        if (!mac) return;
        setLoading(true);
        setError(null);
        setResult(null);
        resetFeedback();

        try {
            const response = await fetch(`http://localhost:4001/api/advanced_nmap/${mac}?logGroundTruth=${canVerify}`);
            const data = await response.json();
            
            if (response.ok) {
                setResult(data);
            } else {
                setError(data.error || 'Scan failed');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '20px', maxWidth: '1600px', margin: '0 auto', fontFamily: 'monospace' }}>
            <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: discoverError || devices.length > 0 ? '15px' : 0 }}>
                    <h3 style={{ margin: 0, flex: 1 }}>Nearby Devices</h3>
                    <button
                        onClick={handleDiscover}
                        disabled={discovering}
                        style={{ padding: '10px 20px', fontSize: '14px', cursor: 'pointer', backgroundColor: '#0d6efd', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold' }}
                    >
                        {discovering ? 'Scanning (few seconds)...' : 'Scan for Devices'}
                    </button>
                </div>

                {discoverError && <div style={{ color: 'red', padding: '10px', border: '1px solid red', marginBottom: '10px' }}>Error: {discoverError}</div>}

                {devices.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {devices.map((d) => (
                            <div
                                key={d.mac}
                                onClick={() => setMac(d.mac)}
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '10px 15px',
                                    backgroundColor: mac === d.mac ? '#cfe2ff' : '#fff',
                                    border: mac === d.mac ? '2px solid #0d6efd' : '1px solid #dee2e6',
                                    borderRadius: '5px',
                                    cursor: 'pointer',
                                }}
                            >
                                <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <strong>{d.name}</strong> &mdash; {d.mac}
                                    <SupportBadge supportLevel={d.support_level} deviceType={d.device_type} />
                                </span>
                                <span style={{ color: '#666' }}>{d.rssi !== null && d.rssi !== undefined ? `${d.rssi} dBm` : 'RSSI N/A'}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {selectedDevice && selectedDevice.device_type === 'ble' && (
                <div style={{ marginBottom: '15px', padding: '12px 15px', backgroundColor: '#fff3cd', color: '#856404', border: '1px solid #ffeeba', borderRadius: '5px', fontSize: '13px' }}>
                    ⚠️ This device is BLE, so some signals (RSSI/baseband metrics) may not be collectible — results may be limited.
                </div>
            )}

            <div style={{ marginBottom: '10px', display: 'flex', gap: '10px' }}>
                <input
                    type="text"
                    value={mac}
                    onChange={(e) => setMac(e.target.value)}
                    placeholder="Enter MAC (e.g. 00:11:22:33:44:55)"
                    style={{ padding: '10px', fontSize: '16px', width: '300px' }}
                />
                <button
                    onClick={handleScan}
                    disabled={loading}
                    style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer', backgroundColor: '#dc3545', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold' }}
                >
                    {loading ? 'Executing Deep OS Protocol Scan...' : 'Run Deep Software OS Scan'}
                </button>
            </div>
            <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#495057', cursor: 'pointer' }}>
                    <input type="checkbox" checked={canVerify} onChange={(e) => setCanVerify(e.target.checked)} />
                    I can verify this device (log this scan for ground-truth calibration)
                </label>
                <div style={{ fontSize: '11px', color: '#868686', marginLeft: '24px' }}>
                    Leave unchecked for a device you can't confirm the real OS/type of afterwards
                    (e.g. a stranger's device during a public sweep) — the scan still runs and
                    shows results below, it just won't be added to the evaluation dataset or ask
                    for feedback.
                </div>
            </div>

            {error && <div style={{ color: 'red', padding: '10px', border: '1px solid red' }}>Error: {error}</div>}

            {result && (
                <>
                <div style={{ marginBottom: '10px', fontSize: '12px', color: result.ground_truth_logged ? '#155724' : '#856404' }}>
                    {result.ground_truth_logged
                        ? '✓ Logged to research_evaluation.csv for ground-truth calibration.'
                        : 'Not logged to the ground-truth dataset (unverified scan).'}
                </div>
                <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>

                    {/* Panel 1: Execution Trace & Protocol Data */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '15px' }}>
                        <div style={{ backgroundColor: '#1e1e1e', color: '#00ff00', padding: '15px', borderRadius: '8px', overflowY: 'auto', maxHeight: '350px' }}>
                            <h3 style={{ color: '#fff', borderBottom: '1px solid #444', paddingBottom: '10px', margin: '0 0 10px 0' }}>Execution Trace</h3>
                            <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: '12px' }}>{result.raw_logs}</pre>
                        </div>
                        
                        <div style={{ backgroundColor: '#fff', border: '1px solid #dee2e6', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', overflowY: 'auto', maxHeight: '400px' }}>
                            <h3 style={{ color: '#d63384', borderBottom: '1px solid #dee2e6', paddingBottom: '10px', margin: '0 0 15px 0' }}>God Mode Packet Telemetry</h3>
                            
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px', marginBottom: '15px' }}>
                                <tbody>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>Absolute RSSI</td>
                                        <td style={{ padding: '8px 0', color: '#0d6efd', textAlign: 'right' }}>{result.features.packet_metrics.absolute_rssi_dbm} dBm</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>Link Quality (0-255)</td>
                                        <td style={{ padding: '8px 0', color: '#0d6efd', textAlign: 'right' }}>{result.features.packet_metrics.link_quality_0_255}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>Transmit Power Level</td>
                                        <td style={{ padding: '8px 0', color: '#0d6efd', textAlign: 'right' }}>{result.features.packet_metrics.tx_power_level_dbm} dBm</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>Baseband Uptime</td>
                                        <td style={{ padding: '8px 0', color: '#198754', textAlign: 'right', fontWeight: 'bold' }}>{result.features.uptime}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>DBus Battery Cache</td>
                                        <td style={{ padding: '8px 0', color: '#198754', textAlign: 'right', fontWeight: 'bold' }}>{result.features.dbus_cache.battery}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>Class of Device (Hex)</td>
                                        <td style={{ padding: '8px 0', textAlign: 'right' }}>{result.features.dbus_cache.class_of_device}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>Modalias / PnP ID</td>
                                        <td style={{ padding: '8px 0', textAlign: 'right' }}>{result.features.dbus_cache.modalias}</td>
                                    </tr>
                                    <tr>
                                        <td style={{ padding: '8px 0', fontWeight: 'bold', color: '#495057' }}>EIR Manufacturer Payload</td>
                                        <td style={{ padding: '8px 0', textAlign: 'right', wordBreak: 'break-all', fontSize: '11px', color: '#d63384' }}>{result.features.dbus_cache.manufacturer_data}</td>
                                    </tr>
                                </tbody>
                            </table>
                            
                            <h4 style={{ color: '#0dcaf0', marginTop: '10px' }}>SDP Record Handles (Sequencing Signature)</h4>
                            <div style={{ fontSize: '12px', wordWrap: 'break-word', color: '#666' }}>
                                {result.features.packet_metrics.sdp_record_handles && result.features.packet_metrics.sdp_record_handles.length > 0 
                                    ? result.features.packet_metrics.sdp_record_handles.join(", ") 
                                    : "None / Blocked"}
                            </div>

                            <h4 style={{ color: '#0dcaf0', marginTop: '10px' }}>GATT UUIDs Enumerated & Inferred</h4>
                            <div style={{ fontSize: '12px', wordWrap: 'break-word', color: '#666', lineHeight: '1.5' }}>
                                {result.features.packet_metrics.gatt_uuids && result.features.packet_metrics.gatt_uuids.length > 0 
                                    ? result.features.packet_metrics.gatt_uuids.map(u => u.includes('1800') || u.includes('1801') ? `${u} (Standard GAP/GATT)` : `${u} (Proprietary OEM Protocol)`).join(" | ") 
                                    : "None / Blocked"}
                            </div>

                            <h4 style={{ color: '#dc3545', marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '15px' }}>Aggressive Interrogation (Deep Scan)</h4>
                            
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', marginBottom: '15px' }}>
                                <tbody>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>AFH Channel Map</td>
                                        <td style={{ padding: '6px 0', color: '#dc3545', textAlign: 'right', wordBreak: 'break-all' }}>{result.aggressive_interrogation.afh_channel_map.map}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>AFH Mode</td>
                                        <td style={{ padding: '6px 0', color: '#dc3545', textAlign: 'right' }}>{result.aggressive_interrogation.afh_channel_map.mode}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>MTU Reliability (600b Ping)</td>
                                        <td style={{ padding: '6px 0', color: result.aggressive_interrogation.mtu_fragmentation_test.includes('Pass') ? '#198754' : '#dc3545', textAlign: 'right' }}>{result.aggressive_interrogation.mtu_fragmentation_test}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>Baseband Features Block</td>
                                        <td style={{ padding: '6px 0', color: '#666', textAlign: 'right' }}>{result.aggressive_interrogation.baseband_features_hex}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>Link Policy Configuration</td>
                                        <td style={{ padding: '6px 0', color: '#fd7e14', textAlign: 'right', fontWeight: 'bold' }}>{result.aggressive_interrogation.link_policy}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>Supervision Timeout Threshold</td>
                                        <td style={{ padding: '6px 0', color: '#fd7e14', textAlign: 'right', fontWeight: 'bold' }}>{result.aggressive_interrogation.supervision_timeout}</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '6px 0', fontWeight: 'bold', color: '#666' }}>Baseband Clock Offset</td>
                                        <td style={{ padding: '6px 0', color: '#666', textAlign: 'right' }}>{result.aggressive_interrogation.clock_offset}</td>
                                    </tr>
                                </tbody>
                            </table>

                            <h5 style={{ color: '#0dcaf0', marginTop: '10px', marginBottom: '5px' }}>Deep GATT Strings</h5>
                            <div style={{ fontSize: '12px', color: '#666', backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '5px' }}>
                                {Object.keys(result.aggressive_interrogation.deep_gatt_characteristics).length > 0 ? (
                                    <ul style={{ margin: 0, paddingLeft: '15px' }}>
                                        {Object.entries(result.aggressive_interrogation.deep_gatt_characteristics).map(([k, v]) => (
                                            <li key={k}><strong>{k}:</strong> <span style={{color: '#198754'}}>{v}</span></li>
                                        ))}
                                    </ul>
                                ) : (
                                    "No readable strings (GATT Blocked / Unauthenticated)"
                                )}
                            </div>

                            <h5 style={{ color: '#6f42c1', marginTop: '15px', marginBottom: '5px' }}>LMP Feature Flags (Vol 2, Part C, 3.3)</h5>
                            <div style={{ fontSize: '12px', color: '#666', backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '5px' }}>
                                {result.features.lmp_features ? (
                                    <>
                                        <div style={{ marginBottom: '8px', wordBreak: 'break-all' }}>
                                            <strong>Raw:</strong> <span style={{ color: '#6f42c1', fontFamily: 'monospace' }}>{result.features.lmp_features.lmp_features_raw}</span>
                                        </div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                            {Object.entries(result.features.lmp_features.lmp_features)
                                                .filter(([, supported]) => supported)
                                                .map(([name]) => (
                                                    <span key={name} style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', backgroundColor: '#e9d8fd', color: '#4a1d8f' }}>
                                                        {name.replace(/_/g, ' ')}
                                                    </span>
                                                ))}
                                        </div>
                                    </>
                                ) : (
                                    "Not exposed (BLE-only device, or blocked by controller)"
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Panel 2: General Telemetry & Hardware */}
                    <div style={{ flex: 1, backgroundColor: '#f8f9fa', color: '#333', padding: '15px', borderRadius: '8px', border: '1px solid #dee2e6', overflowY: 'auto', maxHeight: '800px' }}>
                        <h3 style={{ borderBottom: '1px solid #ccc', paddingBottom: '10px', margin: '0 0 15px 0' }}>General Telemetry</h3>
                        <div style={{ marginBottom: '10px' }}><strong>MAC:</strong> {result.features.mac}</div>
                        <div style={{ marginBottom: '10px' }}><strong>Device Name:</strong> <span style={{ color: '#0056b3', fontWeight: 'bold' }}>{result.features.name}</span></div>
                        <div style={{ marginBottom: '10px' }}><strong>Vendor (OUI):</strong> {result.features.vendor}</div>
                        
                        <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '5px' }}>
                            <div style={{ marginBottom: '5px' }}><strong>Multi-Ping RTT:</strong> {result.features.rtt_ms}</div>
                            <div style={{ marginBottom: '5px' }}><strong>Active Distance:</strong> {result.features.distance_est}</div>
                            <div><strong>Security Posture:</strong> <span style={{color: result.features.security_posture.includes('Secure') ? '#198754' : '#dc3545', fontWeight: 'bold'}}>{result.features.security_posture}</span></div>
                        </div>
                        
                        <h4 style={{ marginTop: '20px', color: '#dc3545' }}>Permissions Granted</h4>
                        <ul style={{ listStyleType: 'none', paddingLeft: 0, fontSize: '13px' }}>
                            {result.features.permissions.map((p, i) => (
                                <li key={i} style={{ padding: '8px', backgroundColor: p.includes('GRANTED') ? '#d4edda' : '#f8d7da', color: p.includes('GRANTED') ? '#155724' : '#721c24', marginBottom: '5px', borderRadius: '4px', borderLeft: p.includes('GRANTED') ? '4px solid #28a745' : '4px solid #dc3545' }}>
                                    {p}
                                </li>
                            ))}
                        </ul>

                        <h4 style={{ marginTop: '20px' }}>Hardware Info</h4>
                        <ul style={{ fontSize: '13px' }}>
                            <li>LMP: {result.features.hardware_info.lmp_version}</li>
                            <li>SubV: {result.features.hardware_info.lmp_subversion}</li>
                        </ul>

                        <h4 style={{ color: '#0d6efd' }}>Chipset Fingerprint (Modalias)</h4>
                        {result.features.dbus_cache.device_id_profile ? (
                            <div style={{ fontSize: '13px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '5px' }}>
                                <div style={{ marginBottom: '5px' }}><strong>Vendor:</strong> {result.features.dbus_cache.device_id_profile.chipset_vendor || 'Unknown'}</div>
                                <div style={{ marginBottom: '5px' }}><strong>Product ID:</strong> 0x{result.features.dbus_cache.device_id_profile.chipset_product_id}</div>
                                {result.features.dbus_cache.device_id_profile.chipset_model ? (
                                    <>
                                        <div style={{ marginBottom: '5px' }}><strong>Chipset:</strong> <span style={{ color: '#198754', fontWeight: 'bold' }}>{result.features.dbus_cache.device_id_profile.chipset_model}</span></div>
                                        <div style={{ marginBottom: '5px' }}><strong>Est. Release Year:</strong> {result.features.dbus_cache.device_id_profile.estimated_chipset_release_year}</div>
                                        <div><strong>Min OS Hint:</strong> {result.features.dbus_cache.device_id_profile.estimated_min_os_hint}</div>
                                    </>
                                ) : (
                                    <div style={{ color: '#856404' }}>Chipset not in local database (vendor/product ID logged for future matching)</div>
                                )}
                            </div>
                        ) : (
                            <div style={{ fontSize: '13px', color: '#666' }}>No Modalias exposed by this device</div>
                        )}

                        <h4>Protocols & Versions</h4>
                        <ul style={{ fontSize: '13px' }}>
                            {result.features.protocols.map((p, i) => <li key={i}>{p}</li>)}
                        </ul>
                    </div>

                    {/* Panel 3: Inference Engine */}
                    <div style={{ flex: 1, backgroundColor: '#e9ecef', color: '#333', padding: '15px', borderRadius: '8px', border: '1px solid #ced4da', display: 'flex', flexDirection: 'column' }}>
                        <h3 style={{ borderBottom: '1px solid #ccc', paddingBottom: '10px', color: '#0056b3', margin: '0 0 15px 0' }}>Software Protocol Inference Engine</h3>
                        
                        <div style={{ padding: '15px', backgroundColor: '#fff', borderRadius: '5px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
                            <div style={{ fontSize: '13px', color: '#666', textTransform: 'uppercase' }}>Predicted Device Type</div>
                            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#212529', marginBottom: '15px' }}>
                                {result.inferences.device_type}
                            </div>

                            <div style={{ fontSize: '13px', color: '#666', textTransform: 'uppercase' }}>Target OS Kernel</div>
                            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#007bff', marginBottom: '15px' }}>
                                {result.inferences.os}
                            </div>

                            <div style={{ fontSize: '13px', color: '#666', textTransform: 'uppercase' }}>Major/Minor OS Version</div>
                            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#28a745', marginBottom: '15px' }}>
                                {result.inferences.major_minor_version}
                            </div>

                            <div style={{ fontSize: '13px', color: '#666', textTransform: 'uppercase' }}>OS Confidence Score</div>
                            <div style={{ fontSize: '18px', fontWeight: 'bold', color: result.inferences.confidence.includes('High') ? '#28a745' : '#ffc107' }}>
                                {result.inferences.confidence}
                            </div>

                            {result.inferences.inconsistency_flags && result.inferences.inconsistency_flags.length > 0 && (
                                <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '5px', fontSize: '13px', borderLeft: '4px solid #dc3545' }}>
                                    ⚠️ <strong>Inconsistency Detected:</strong>
                                    <ul style={{ margin: '5px 0 0', paddingLeft: '18px' }}>
                                        {result.inferences.inconsistency_flags.map((flag, i) => (
                                            <li key={i}>{flag.replace(/_/g, ' ')}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {result.inferences.has_conflicting_signals && (
                                <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '5px', fontSize: '13px', borderLeft: '4px solid #dc3545' }}>
                                    ⚠️ <strong>Conflicting Signals Detected:</strong> at least one
                                    signal independent of this prediction disagreed with it - see
                                    the evidence chain below before trusting this result fully.
                                </div>
                            )}
                        </div>

                        {result.inferences.evidence_chain && result.inferences.evidence_chain.length > 0 && (
                            <>
                                <h4 style={{ marginTop: '20px', color: '#6f42c1', borderBottom: '1px solid #ccc', paddingBottom: '5px' }}>Evidence Chain</h4>
                                <div style={{ padding: '15px', backgroundColor: '#fff', borderRadius: '5px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', fontSize: '13px' }}>
                                    {result.inferences.evidence_chain.map((entry, i) => {
                                        const directionStyle = {
                                            supports: { label: 'SUPPORTS', color: '#155724', backgroundColor: '#d4edda' },
                                            conflicts: { label: 'CONFLICTS', color: '#721c24', backgroundColor: '#f8d7da' },
                                            primary: { label: 'PRIMARY (scoring input)', color: '#495057', backgroundColor: '#e2e3e5' },
                                            unused: { label: 'UNUSED', color: '#856404', backgroundColor: '#fff3cd' },
                                        }[entry.direction] || { label: entry.direction, color: '#495057', backgroundColor: '#e2e3e5' };
                                        return (
                                            <div key={i} style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: i < result.inferences.evidence_chain.length - 1 ? '1px solid #eee' : 'none' }}>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                                    <strong style={{ color: '#212529' }}>{entry.signal_name.replace(/_/g, ' ')}</strong>
                                                    <span style={{ fontSize: '10px', fontWeight: 'bold', padding: '2px 6px', borderRadius: '8px', color: directionStyle.color, backgroundColor: directionStyle.backgroundColor, whiteSpace: 'nowrap' }}>
                                                        {directionStyle.label}
                                                    </span>
                                                </div>
                                                <div style={{ color: '#495057' }}>Observed: {String(entry.observed_value)}</div>
                                                <div style={{ color: '#495057' }}>{entry.inference}</div>
                                                <div style={{ color: '#6c757d', fontStyle: 'italic' }}>{entry.contribution}</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </>
                        )}

                        <h4 style={{ marginTop: '20px', color: '#6f42c1', borderBottom: '1px solid #ccc', paddingBottom: '5px' }}>Deep Metadata Extraction</h4>
                        <div style={{ padding: '15px', backgroundColor: '#fff', borderRadius: '5px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', fontSize: '14px' }}>
                            <div style={{ marginBottom: '12px' }}>
                                <strong style={{ color: '#495057' }}>Estimated Spec/Mfg Year:</strong> <br/>
                                <span style={{ color: '#212529' }}>{result.deep_metadata.hardware_age}</span>
                            </div>
                            <div style={{ marginBottom: '12px' }}>
                                <strong style={{ color: '#495057' }}>Target Market:</strong> <br/>
                                <span style={{ color: '#212529' }}>{result.deep_metadata.market}</span>
                            </div>
                            <div style={{ marginBottom: '12px' }}>
                                <strong style={{ color: '#495057' }}>Power State / Latency Profile:</strong> <br/>
                                <span style={{ color: '#212529' }}>{result.deep_metadata.power_state}</span>
                            </div>
                            
                            <div style={{ marginBottom: '12px', borderTop: '1px solid #eee', paddingTop: '10px' }}>
                                <strong style={{ color: '#d63384' }}>Raw Protocol Insights:</strong> <br/>
                                <ul style={{ listStyleType: 'square', paddingLeft: '20px', color: '#212529', marginTop: '5px' }}>
                                    {result.deep_metadata.protocol_insights.map((insight, i) => (
                                        <li key={i}>{insight}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                </>
            )}

            {result && result.ground_truth_logged && (
                <div style={{ marginTop: '20px', padding: '15px 20px', backgroundColor: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: '8px' }}>
                    {feedbackSubmitted ? (
                        <div style={{ color: '#198754', fontWeight: 'bold' }}>✓ Thanks — feedback recorded.</div>
                    ) : (
                        <>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                                <strong>Was this prediction correct?</strong>
                                <button
                                    onClick={() => submitFeedback(true)}
                                    disabled={feedbackSubmitting}
                                    style={{ padding: '6px 16px', cursor: 'pointer', backgroundColor: '#198754', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold' }}
                                >
                                    Yes
                                </button>
                                <button
                                    onClick={() => setFeedbackChoice('no')}
                                    disabled={feedbackSubmitting}
                                    style={{ padding: '6px 16px', cursor: 'pointer', backgroundColor: '#dc3545', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold' }}
                                >
                                    No
                                </button>
                            </div>

                            {feedbackChoice === 'no' && (
                                <div style={{ marginTop: '15px', display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '500px' }}>
                                    <input
                                        type="text"
                                        value={actualValue}
                                        onChange={(e) => setActualValue(e.target.value)}
                                        placeholder="Actual OS/Version:"
                                        style={{ padding: '8px', fontSize: '14px' }}
                                    />
                                    <textarea
                                        value={feedbackNotes}
                                        onChange={(e) => setFeedbackNotes(e.target.value)}
                                        placeholder="Notes (optional)"
                                        rows={2}
                                        style={{ padding: '8px', fontSize: '14px', fontFamily: 'monospace' }}
                                    />
                                    <button
                                        onClick={() => submitFeedback(false)}
                                        disabled={feedbackSubmitting}
                                        style={{ padding: '8px 16px', cursor: 'pointer', backgroundColor: '#0d6efd', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', alignSelf: 'flex-start' }}
                                    >
                                        {feedbackSubmitting ? 'Submitting...' : 'Submit Feedback'}
                                    </button>
                                </div>
                            )}

                            {feedbackError && <div style={{ color: 'red', marginTop: '10px' }}>Error: {feedbackError}</div>}
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default AdvancedNmap;
