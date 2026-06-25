const fs = require('fs');
const glob = require('glob');

const files = glob.sync('app/src/main/java/com/example/ui/screens/*.kt');
files.forEach(file => {
    let content = fs.readFileSync(file, 'utf8');
    content = content.replace(/Color\(0xFFFA1414\)/g, 'MaterialTheme.colorScheme.primary');
    fs.writeFileSync(file, content);
});
