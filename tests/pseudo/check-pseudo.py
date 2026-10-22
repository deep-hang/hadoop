"""Single-node HDFS lifecycle proof, isolated from normal/member environments."""
from pathlib import Path
import json
import re
import socket
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'standalone'))
from support import ROOT, Suite, custom_input_checks, require


def main():
    suite = Suite('pseudo')
    success, error = False, None
    node = '/workspace/modes/pseudo/node.sh'
    try:
        config = json.loads(suite.compose('config', '--format', 'json').stdout)['services']['pseudo']
        require(float(config['cpus']) == 2, 'Wrong CPU limit')
        require(str(config['mem_limit']) == '2147483648', 'Wrong memory limit')
        require(config['ports'][0]['host_ip'] == '127.0.0.1', 'Web must bind loopback')
        suite.compose('config', '--quiet')
        suite.fail(suite.compose('run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', node, 'start', check=False), 'not initialized')
        suite.mark('uninitialized start fails without implicit formatting')
        # Separate NN and DN guard cases; all paths below are in the fresh test volume.
        for directory in ('namenode', 'datanode'):
            script = ('mkdir -p /var/lib/hadoop/hdfs/' + directory + '; '
                      'touch /var/lib/hadoop/hdfs/' + directory + '/guard-sentinel; '
                      'if bash ' + node + ' init; then exit 99; fi; '
                      'test -f /var/lib/hadoop/hdfs/' + directory + '/guard-sentinel; '
                      'test ! -e /var/lib/hadoop/hdfs/namenode/current/VERSION; '
                      'rm /var/lib/hadoop/hdfs/' + directory + '/guard-sentinel')
            guarded = suite.compose('run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', '-ec', script)
            require('Refusing to format' in guarded.stderr+guarded.stdout, 'Guard did not execute')
            suite.mark('nonempty ' + directory + ' protected against formatting')
        suite.compose('run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', node, 'init')
        read_version = ['run', '--rm', '-T', '--no-deps', 'pseudo', 'cat', '/var/lib/hadoop/hdfs/namenode/current/VERSION']
        version = suite.compose(*read_version).stdout
        again = suite.compose('run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', node, 'init')
        require('Already initialized' in again.stdout, 'Repeated init did not preserve metadata')
        require(suite.compose(*read_version).stdout == version, 'Repeated init changed VERSION')
        suite.mark('explicit and repeated initialization preserves metadata')
        suite.compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'pseudo', timeout=210)
        suite.inside('bash', '/workspace/modes/pseudo/healthcheck.sh')
        suite.fail(suite.compose('run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', node, 'init', check=False), 'already running')
        processes = suite.inside('jps').stdout
        require('NameNode' in processes and 'DataNode' in processes, 'Missing HDFS services')
        require('ResourceManager' not in processes and 'NodeManager' not in processes, 'Unexpected YARN service')
        suite.mark('one live DataNode, safe mode OFF, two HDFS services; running init refused')
        mapping = suite.compose('port', 'pseudo', '9870').stdout.strip()
        port = int(mapping.rsplit(':', 1)[1])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo', timeout=10) as response:
            bean = json.load(response)['beans'][0]
        require(len(json.loads(bean['LiveNodes'])) == 1, 'Web does not show one live DataNode')
        suite.results['web_port'] = port
        suite.mark('loopback Web endpoint reports one live DataNode')
        run_id = 'sample'
        job = suite.inside('bash', '/workspace/modes/pseudo/run.sh', run_id)
        require('MODE_CONFIG_PASS fs.defaultFS=hdfs://pseudo:9000' in job.stdout, 'Wrong filesystem')
        require('job_local' in job.stdout+job.stderr, 'No local MapReduce job evidence')
        require(not re.search(r'application_\d+_\d+', job.stdout+job.stderr), 'Unexpected YARN application')
        source = suite.inside('hdfs', 'dfs', '-cat', '/project/input/member5/sample/sample.txt').stdout
        require(source == (ROOT / 'modes/standalone/input/sample.txt').read_text(), 'HDFS upload differs')
        suite.inside('hdfs', 'dfs', '-ls', '/project/input/member5/sample')
        output = suite.inside('hdfs', 'dfs', '-cat', '/project/output/member5/sample/part-r-*').stdout
        require(sorted(output.splitlines()) == ['hadoop\t1', 'hello\t2'], 'HDFS result differs')
        suite.fail(suite.inside('bash', '/workspace/modes/pseudo/run.sh', run_id, check=False), 'already exists')
        require(suite.inside('hdfs', 'dfs', '-cat', '/project/output/member5/sample/part-r-*').stdout == output,
                'Repeated job changed old data')
        suite.mark('HDFS mkdir/put/ls/cat, local MapReduce and existing-path protection')
        custom_id = custom_input_checks(suite)
        suite.compose('restart', 'pseudo', timeout=120)
        suite.compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'pseudo', timeout=210)
        suite.inside('bash', '/workspace/modes/pseudo/verify.sh', run_id)
        suite.inside('bash', '/workspace/modes/pseudo/verify.sh', custom_id)
        require(suite.inside('cat', '/var/lib/hadoop/hdfs/namenode/current/VERSION').stdout == version, 'Restart changed metadata')
        require(suite.inside('hdfs', 'dfs', '-cat', '/project/input/member5/sample/sample.txt').stdout == source, 'Restart lost input')
        suite.mark('restart preserves input, output and cluster metadata')
        suite.compose('down', timeout=120)
        # Occupy a loopback port and prove failed startup does not stop its owner.
        with socket.socket() as blocker:
            blocker.bind(('127.0.0.1', 0))
            blocker.listen(1)
            suite.env['M5_PSEUDO_WEB_PORT'] = str(blocker.getsockname()[1])
            conflict = suite.compose('up', '-d', '--no-build', 'pseudo', check=False, timeout=60)
            require(conflict.returncode != 0, 'Occupied port was not rejected')
            blocker.getsockname()  # Owner remains alive and bound.
            suite.compose('down', timeout=120)
        suite.env['M5_PSEUDO_WEB_PORT'] = '0'
        suite.mark('occupied Web port rejected without disturbing its owner')
        suite.compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'pseudo', timeout=210)
        suite.inside('bash', '/workspace/modes/pseudo/verify.sh', run_id)
        suite.inside('bash', '/workspace/modes/pseudo/verify.sh', custom_id)
        require(suite.inside('cat', '/var/lib/hadoop/hdfs/namenode/current/VERSION').stdout == version, 'Recreation changed metadata')
        require(suite.inside('hdfs', 'dfs', '-cat', '/project/input/member5/sample/sample.txt').stdout == source, 'Recreation lost input')
        suite.mark('container recreation preserves input, output and cluster metadata')
        suite.wrapper_checks()
        container = suite.compose('ps', '-q', 'pseudo').stdout.strip()
        suite.inside('bash', '-ec', 'pid=$(jps | awk \'$2 == "DataNode" {print $1}\'); test -n "$pid"; kill -TERM "$pid"')
        deadline = time.monotonic()+35
        while time.monotonic() < deadline:
            state = json.loads(suite.run(['docker', 'inspect', container]).stdout)[0]['State']
            if not state['Running']:
                require(state['ExitCode'] != 0, 'Service failure returned success')
                require(not state['OOMKilled'], 'Unexpected OOM instead of peer cleanup')
                break
            time.sleep(1)
        else:
            raise AssertionError('Container survived DataNode failure')
        suite.mark('DataNode failure stops peer and exits container nonzero')
        success = True
    except Exception as exception:
        error = str(exception)
        print('FAIL: ' + error, flush=True)
    finally:
        suite.finish(success, error)


if __name__ == '__main__':
    main()
