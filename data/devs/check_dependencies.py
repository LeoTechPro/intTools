import subprocess


def main() -> None:
    result = subprocess.run(
        ['pip', 'list', '--outdated', '--format=freeze'],
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout.strip()
    if output:
        print('Outdated packages:\n' + output)
    else:
        print('All packages up to date.')


if __name__ == '__main__':
    main()
