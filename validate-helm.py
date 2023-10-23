#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

# import hunter
# hunter.trace()

def find_helm_chart(path):
    counter = 0
    while path != '/' and counter < 4:
        if path == '':
            return None
        if 'Chart.yaml' in os.listdir(path):
            return path
        path = os.path.dirname(path)
        counter += 1
    return None

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        # print(f'Command "{cmd}" failed with error:\n{result.stderr}')
        return False, result.stderr
    return True, result.stdout

def test_helm_kustomize(path, target='client'):
    success, output = run_command('helm lint ' + path)
    if not success:
        # print(f'Test failed (helm lint) for {path}:\n{output}')
        return False, output
    success, output = run_command('helm template ' + path)
    if not success:
        # print(f'Test failed (helm template) for {path}:\n{output}')
        return False, output
    cmd = f'helm template "{path}" | kubectl apply --dry-run={target} -f - 2>&1 | grep -v "missing the kubectl.kubernetes.io/last-applied"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    # print(f'Command "{cmd}" result:\n{result.returncode}')
    return 'Error from server' not in result.stdout \
        and 'request is invalid' not in result.stdout \
        and result.returncode == 0, result.stdout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='+')
    args = parser.parse_args()

    tested_dirs = set()
    all_tests_passed = True

    for filename in args.filenames:
        dir_path = find_helm_chart(os.path.dirname(filename))

        if dir_path is not None and dir_path not in tested_dirs:
            tested_dirs.add(dir_path)
            # print(f'Test dir={dir_path} for filename={filename} tested_dirs={tested_dirs}')
            success, output = run_command('kubectl config current-context')
            if success:
                success, output = test_helm_kustomize(dir_path, target='server')
                if not success:
                    print(f'Test failed (helm template + dry-run server) for {filename} for dir={dir_path}:\n{output}')
                    all_tests_passed = False
                else:
                     print(f'Test result (helm template + dry-run server) for {filename} for dir={dir_path}:\n{output}')
            else:
                success, output = run_command('helm lint ' + dir_path)
                if not success:
                    print(f'Test failed (helm lint) for {filename} for dir={dir_path}:\n{output}')
                    all_tests_passed = False
                else:
                     print(f'Test result (helm lint) for {filename} for dir={dir_path}:\n{output}')

    if not all_tests_passed:
        sys.exit(1)

if __name__ == '__main__':
    main()
