"""Static contract validation, using Python's standard library only.

This does not replace the required container build and runtime verification.
Run from any directory: python tests/common/check-contract.py
"""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = dict(
    line.split('=', 1)
    for line in (ROOT / '.development').read_text(encoding='utf-8').splitlines()
    if line and not line.startswith('#')
)


class PublicContract(unittest.TestCase):
    def test_frozen_toolchain(self):
        dockerfile = (ROOT / 'docker/Dockerfile').read_text(encoding='utf-8')
        self.assertRegex(dockerfile, r'FROM eclipse-temurin:8u442-b06-jdk-jammy@sha256:[0-9a-f]{64}')
        self.assertIn('HADOOP_VERSION=' + CONTRACT['HADOOP_VERSION'], dockerfile)
        self.assertEqual(CONTRACT['JDK_VERSION'], '1.8.0_442')
        self.assertRegex(dockerfile, r"echo '[0-9a-f]{128}  /tmp/hadoop.tar.gz' \| sha512sum -c -")

    def test_cluster_contract(self):
        self.assertEqual([CONTRACT[k] for k in ('MASTER_HOST', 'WORKER1_HOST', 'WORKER2_HOST')],
                         ['master', 'worker1', 'worker2'])
        self.assertEqual(CONTRACT['HDFS_URI'], 'hdfs://master:9000')
        self.assertEqual(CONTRACT['NAMENODE_WEB_PORT'], '9870')
        self.assertEqual(CONTRACT['YARN_WEB_PORT'], '8088')
        self.assertEqual((ROOT / 'config/common/workers').read_text().splitlines(),
                         ['worker1', 'worker2'])

    def test_base_has_no_cluster_configuration(self):
        root = ET.parse(ROOT / 'config/common/core-site.xml').getroot()
        self.assertEqual(root.tag, 'configuration')
        self.assertEqual(list(root), [])

    def test_shared_paths(self):
        for key, expected in {
            'JAVA_HOME': '/opt/java/openjdk', 'HADOOP_HOME': '/opt/hadoop',
            'HADOOP_CONF_DIR': '/opt/hadoop/etc/hadoop', 'WORKSPACE': '/workspace',
            'WORDCOUNT_DIR': '/workspace/apps/wordcount',
            'MERGEFILE_DIR': '/workspace/apps/mergefile',
        }.items():
            self.assertEqual(CONTRACT[key], expected)

    def test_handoff_directories(self):
        for folder in ['docker', 'compose', 'config/common', 'config/hdfs', 'config/yarn',
                       'modes/standalone', 'modes/pseudo', 'apps/wordcount/src',
                       'apps/wordcount/input', 'apps/mergefile/src', 'apps/mergefile/input',
                       'tests/common', 'tests/distributed', 'tests/hdfs', 'tests/yarn-mapreduce',
                       'tests/standalone', 'tests/pseudo', 'tests/wordcount', 'tests/mergefile',
                       'tests/integration', 'docs/modules/distributed', 'docs/modules/hdfs',
                       'docs/modules/yarn-mapreduce', 'docs/modules/standalone-pseudo',
                       'docs/modules/wordcount', 'docs/modules/mergefile', '.changes']:
            self.assertTrue((ROOT / folder).is_dir(), folder)

    def test_shell_files_use_lf(self):
        for path in [ROOT / '.development', *ROOT.rglob('*.sh')]:
            data = path.read_bytes()
            self.assertNotIn(b'\r', data, str(path))
            self.assertFalse(data.startswith(b'\xef\xbb\xbf'), str(path))

    def test_document_links_resolve(self):
        for path in [ROOT / 'README.md', *list((ROOT / 'docs').glob('*.md'))]:
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if '://' not in target:
                    self.assertTrue((path.parent / target.split('#', 1)[0]).exists(),
                                    f'{path}: {target}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
