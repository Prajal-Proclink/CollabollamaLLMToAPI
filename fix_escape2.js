const fs = require('fs');
let content = fs.readFileSync('C:/Users/prajal.patel/source/repos/CollabollamaLLMToAPI/static/app.js', 'utf8');

// Fix & -> &, < -> <, > -> >
content = content.replace("'&': '&'", "'&': '&'");
content = content.replace("'<': '<'", "'<': '<'");
content = content.replace("'>': '>'", "'>': '>'");

fs.writeFileSync('C:/Users/prajal.patel/source/repos/CollabollamaLLMToAPI/static/app.js', content);
console.log('Fixed');