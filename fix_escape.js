const fs = require('fs');
let content = fs.readFileSync('C:/Users/prajal.patel/source/repos/CollabollamaLLMToAPI/static/app.js', 'utf8');

// Current mapping
const oldMapping = "tag => ({ '&': '&', '<': '<', '>': '>', \"'\": ''', '\"': '"' }[tag] || tag)";

const idx = content.indexOf(oldMapping);
if (idx === -1) {
    console.log('Pattern not found');
    process.exit(1);
}

console.log('Found at index:', idx);

// New mapping with ALL proper HTML entities
// & -> & (38 + #65;), < -> <, > -> >, ' -> ', " -> "
const newMapping = "tag => ({ '&': '&', '<': '<', '>': '>', \"'\": ''', '\"': '"' }[tag] || tag)";
console.log('New mapping:', newMapping);

content = content.substring(0, idx) + newMapping + content.substring(idx + oldMapping.length);

fs.writeFileSync('C:/Users/prajal.patel/source/repos/CollabollamaLLMToAPI/static/app.js', content);
console.log('Fixed!');