"""Run real local MapReduce and verify failure behavior in a random project."""
from pathlib import Path
import json
import re
from support import ROOT, Suite, custom_input_checks, require, tree_digest


def main():
    suite = Suite('standalone')
    success, error = False, None
    try:
        config = json.loads(suite.compose('config', '--format', 'json').stdout)['services']['standalone']
        require(config['mem_limit'] == '1073741824' or config['mem_limit'] == 1073741824, 'Wrong memory limit')
        require(float(config['cpus']) == 1, 'Wrong CPU limit')
        require(next(v for v in config['volumes'] if v['target'] == '/workspace')['read_only'], 'Repository must be read-only')
        suite.mark('Compose isolates repository and limits standalone resources')
        run_id = suite.project
        result = suite.inside('bash', '/workspace/modes/standalone/run.sh', run_id)
        require('MODE_CONFIG_PASS fs.defaultFS=file:///' in result.stdout, 'Wrong effective configuration')
        require('job_local' in result.stdout+result.stderr, 'No local MapReduce execution evidence')
        require(not re.search(r'application_\d+_\d+', result.stdout+result.stderr), 'Unexpected YARN application')
        output = ROOT / f'runtime/member5/standalone/{run_id}/output'
        actual = ''.join(p.read_text(encoding='utf-8') for p in sorted(output.glob('part-r-*')))
        require(sorted(actual.splitlines()) == ['hadoop\t1', 'hello\t2'], 'Incorrect word counts')
        suite.mark('real local MapReduce, fixed counts, no HDFS/YARN daemons')
        before = tree_digest(output)
        suite.fail(suite.inside('bash', '/workspace/modes/standalone/run.sh', run_id, check=False), 'already exists')
        require(tree_digest(output) == before, 'Repeated run changed old output')
        suite.mark('existing output rejected without changing data')
        missing_id = run_id + '-missing'
        suite.fail(suite.inside('bash', '/workspace/modes/standalone/run.sh', missing_id,
                                '/tmp/member5-input-does-not-exist', check=False), 'missing or empty')
        require(not (output.parent.parent / missing_id).exists(), 'Missing input created output')
        suite.mark('missing input fails without creating a run')
        part = next(output.glob('part-r-*'))
        original = part.read_bytes()
        for label, data in [('wrong count', b'hadoop\t1\nhello\t3\n'),
                            ('missing word', b'hello\t2\n'),
                            ('extra word', original+b'other\t1\n'),
                            ('duplicate word', original+b'hello\t2\n')]:
            part.write_bytes(data)
            suite.fail(suite.inside('bash', '/workspace/modes/standalone/verify.sh', run_id, check=False), 'RESULT_MISMATCH')
            part.write_bytes(original)
            suite.mark('verification rejects ' + label)
        marker = output / '_SUCCESS'
        marker.unlink()
        suite.fail(suite.inside('bash', '/workspace/modes/standalone/verify.sh', run_id, check=False), 'Missing success marker')
        marker.touch()
        suite.inside('bash', '/workspace/modes/standalone/verify.sh', run_id)
        suite.mark('success marker is required')
        custom_input_checks(suite)
        suite.wrapper_checks()
        success = True
    except Exception as exception:
        error = str(exception)
        print('FAIL: ' + error, flush=True)
    finally:
        suite.finish(success, error)


if __name__ == '__main__':
    main()
