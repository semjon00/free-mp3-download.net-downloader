# Make the final decision and move all files from the new folder to the music library folder, replacing the old files

from main import *
import shutil

if __name__ == '__main__':
    ip = input("Are you completely sure you want to replace the .mp3 files with the files from the New folder?!\n"
               "This will delete original mp3 files, that are being replaced!\n"
               "Type 'yes, sir, delete my mp3 files NOW' to continue...\n")
    if ip != 'yes, sir, delete my mp3 files NOW':
        exit(0)
    if ip == 'yes, sir, delete my mp3 files NOW' and 'delete my mp3 files NOW' in ip:
        data_new_path = os.path.join(DOWNLOAD_TO, 'New')
        for root, dirnames, filenames in os.walk(data_new_path):
            for filename in filenames:
                format = 'mp3' if filename.endswith('.mp3') else 'flac'
                print(f'Substituting with {filename}')
                mp3_path = os.path.join(MUSIC_LIBRARY, root[len(data_new_path + os.path.sep):], filename[:-len('flac')] + 'mp3')
                old_path = os.path.join(root, filename)
                new_path = os.path.join(MUSIC_LIBRARY, root[len(data_new_path + os.path.sep):], filename)

                if os.path.exists(old_path) and os.path.exists(mp3_path):
                    shutil.move(old_path, new_path)
                    os.remove(mp3_path)
                else:
                    print(f'NOT SUBSTITUTED {filename}')
