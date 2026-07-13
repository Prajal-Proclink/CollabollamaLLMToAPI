const fs = require('fs');
const content = fs.readFileSync('C:/Users/prajal.patel/source/repos/CollabollamaLLMToAPI/static/styles.css', 'utf8');
const lines = content.split('\n');

// Remove lines 1610-1613 (0-indexed: 1609-1612)
const newLines = [
    ...lines.slice(0, 1609),  // up to line 1609
    ...lines.slice(1613)       // skip 1610-1613, continue from 1614
];

fs.writeFileSync('C:/Users/prajal.patel/source/repos/CollabollamaLLMToAPI/static/styles.css', newLines.join('\n'));
console.log('Fixed!');