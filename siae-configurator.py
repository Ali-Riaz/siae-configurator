import os

def main():

    file_name = 'ptp-1841-211W-siae-2g'
    dirName = 'Siae Configs'

    # Specify the directory path
    dir_path = os.path.join(os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop'), dirName)
    print(dir_path)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


    file_path = os.path.join(dir_path, file_name) + '.txt'

    with open(file_path, 'w') as fp:
        fp.write('This is first line')
        pass

if __name__ == '__main__':
    main()