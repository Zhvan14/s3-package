#!/usr/bin/env node
const path = require('path');
const {
  exec
} = require('child_process');

const commandName = path.basename(process.argv[1]);
const sInterpreterPath = path.join(__dirname, 's_interpreter.py');

if (commandName === 's3interpret') {
  // Multiline interpreter mode
  const command = `python ${sInterpreterPath}`;
  
  // This will run the Python script without arguments, which
  // triggers its interactive input mode.
  const child = exec(command);

  child.stdout.pipe(process.stdout);
  child.stderr.pipe(process.stderr);
  process.stdin.pipe(child.stdin);

  child.on('close', (code) => {
    process.exit(code);
  });
} else if (commandName === 's3run') {
  // Run a file
  const filePath = process.argv[2];

  if (!filePath) {
    console.error("Error: No file path provided.");
    process.exit(1);
  }

  const command = `python ${sInterpreterPath} ${filePath}`;
  
  exec(command, (error, stdout, stderr) => {
    if (error) {
      console.error(`Execution error: ${stderr}`);
      return;
    }
    console.log(stdout);
  });
} else {
  console.error("Error: Command not recognized. Use 's3interpret' or 's3run'.");
  process.exit(1);
}
