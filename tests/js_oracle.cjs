// Reference functions are copied without formula edits from the supplied HTML.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({N: request.paths?.length ?? 1, CONC: 3});
const source = fs.readFileSync(path.join(__dirname, 'fixtures/original_math.js'), 'utf8');
new vm.Script(source).runInContext(context);
const positions = (request.positions ?? []).map(spec => {
  const position = context.pos(spec.capital, spec.center, spec.width);
  return {pl: position.pl, pu: position.pu, L: position.L, values: spec.prices.map(p => position.val(p))};
});
const results = {};
for (const mode of ['full','fixed','dyn']) {
  if (request.paths) {
    results[mode] = request.paths.map(p => context.run(p, mode, request.width, request.options));
    results[mode + '_aggregate'] = context.agg(request.paths, mode, request.width, request.options);
  }
}
process.stdout.write(JSON.stringify({positions, results}));
