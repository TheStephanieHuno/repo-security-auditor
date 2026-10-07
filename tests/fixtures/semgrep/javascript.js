// Semgrep test target for app/scanners/rules/semgrep/javascript.yml.
// Annotations: "ruleid:" must match on the next line, "ok:" must not.
const cp = require('child_process');
const { execSync } = require('child_process');

function handler(req, res, db, element) {
  const input = req.query.input;

  // ruleid: rsa-js-eval
  eval(input);
  // ok: rsa-js-eval
  eval("2 + 2");

  // ruleid: rsa-js-new-function
  const fn = new Function('a', input);
  // ok: rsa-js-new-function
  const add = new Function('a', 'b', 'return a + b');

  // ruleid: rsa-js-child-process-exec
  cp.exec('ls ' + input);
  // ruleid: rsa-js-child-process-exec
  execSync(`cat ${input}`);
  // ruleid: rsa-js-child-process-exec
  require('child_process').exec(input);
  // ok: rsa-js-child-process-exec
  cp.exec('ls -la');
  // ok: rsa-js-child-process-exec
  cp.execFile('ls', [input]);

  // ruleid: rsa-js-dom-xss-sink
  element.innerHTML = input;
  // ruleid: rsa-js-dom-xss-sink
  document.write(input);
  // ok: rsa-js-dom-xss-sink
  element.innerHTML = "<b>static</b>";
  // ok: rsa-js-dom-xss-sink
  element.textContent = input;

  // ruleid: rsa-js-sql-string-building
  db.query("SELECT * FROM users WHERE id = " + input);
  // ruleid: rsa-js-sql-string-building
  db.query(`SELECT * FROM users WHERE id = ${input}`);
  // ok: rsa-js-sql-string-building
  db.query("SELECT * FROM users WHERE id = $1", [input]);

  // ruleid: rsa-js-tls-verification-disabled
  const agent = new https.Agent({ keepAlive: true, rejectUnauthorized: false });
  // ok: rsa-js-tls-verification-disabled
  const safeAgent = new https.Agent({ keepAlive: true });

  return [fn, add, agent, safeAgent];
}

module.exports = handler;
