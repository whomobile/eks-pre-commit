#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys
import glob

# import hunter
# hunter.trace()

def find_kustomization(path):
    counter = 0
    while path != '/' and counter < 4:
        if path == '':
            return None
        if 'kustomization.yaml' in os.listdir(path):
            return path
        path = os.path.dirname(path)
        counter += 1
    return None

def find_base_overlay_kustomization(path):
    if path.endswith('/base'):
        overlays_dirs = glob.glob(os.path.join(os.path.dirname(path), 'overlays/*'))
        return [dir for dir in overlays_dirs if 'kustomization.yaml' in os.listdir(dir)]
    else:
        counter = 0
        while path != '/' and counter < 4:
            if path == '':
                return None
            if 'kustomization.yaml' in os.listdir(path):
                return [path]
            path = os.path.dirname(path)
            counter += 1
        return None

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        # print(f'Command "{cmd}" failed with error:\n{result.stderr}')
        return False, result.stderr
    return True, result.stdout

def test_kustomization(path, target='client', mode='apply'):
    # success, output = run_command('kubectl kustomize ' + path)
    # if not success:
    #     print(f'Test failed (kubectl kustomize) for {path}:\n{output}')
    #     return False, output
    cmd = f'kubectl kustomize "{path}" | kubectl {mode} --dry-run={target} -f - 2>&1 | grep -v "missing the kubectl.kubernetes.io/last-applied"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f'Command "{cmd}" result: {result.returncode}')
    return 'Error from server' not in result.stdout \
        and ' is invalid' not in result.stdout \
        and result.returncode == 0, result.stdout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='+')
    args = parser.parse_args()

    tested_dirs = set()
    all_tests_passed = True

    for filename in args.filenames:
        dir_paths = find_base_overlay_kustomization(os.path.dirname(filename))
        if dir_paths is None:
            continue
        for dir_path in dir_paths:
            if dir_path is not None and dir_path not in tested_dirs:
                tested_dirs.add(dir_path)
                # print(f'Test dir={dir_path} for filename={filename}')
                success, output = run_command('kubectl config current-context')
                if success:
                    success, output = test_kustomization(dir_path, target='server', mode='apply')
                    if not success:
                        print(f'Test failed (server side) for {filename} for dir={dir_path}:\n{output}')
                        all_tests_passed = False
                    else:
                        print(f'Test result for {filename} for dir={dir_path}:\n{output}')
                else:
                    success, output = test_kustomization(dir_path, target='client', mode='create')
                    if not success:
                        print(f'Test failed (client side) for {filename} for dir={dir_path}:\n{output}')
                        all_tests_passed = False
                    else:
                        print(f'Test result for {filename} for dir={dir_path}:\n{output}')

    if not all_tests_passed:
        sys.exit(1)

if __name__ == '__main__':
    main()
