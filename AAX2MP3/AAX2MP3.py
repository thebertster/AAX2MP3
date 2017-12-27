import os
import argparse
import tempfile
import json
import html
import subprocess
import re

class AAXConverter:
    def __init__(self, auth_code, aax_file, base_dir):
        self.auth_code = auth_code
        self.aax_file = aax_file
        self.base_dir = base_dir

    def convert_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_cnv_filename = '{}\\tmpcnv.mp3'.format(tmp_dir)

            probe = subprocess.run(['ffprobe', '-v', 'quiet',
                                    '-print_format', 'json',
                                    '-show_format',
                                    '-show_chapters',
                                    '-show_error', '-i',
                                    self.aax_file],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            metadata = json.loads(probe.stdout)

            if 'error' in metadata:
                raise Exception('ffprobe returned error: {}'
                                .format(metadata['error']['string']))

            m_format = metadata['format']
            m_tags = m_format['tags']
            m_filename = m_format['filename']
            m_bit_rate = m_format['bit_rate']
            m_duration = m_format['duration']
            m_genre = m_tags['genre']
            m_title = m_tags['title']
            m_artist = m_tags['artist']
            m_album_artist = m_tags['album_artist']
            m_date = m_tags['date']
            m_comment = m_tags['comment']
            m_copyright = html.unescape(m_tags['copyright'])
            m_chapters = metadata['chapters']
            m_num_chapters = len(m_chapters)

            if m_title.endswith(' (Unabridged)'):
                m_title = m_title[:-len(' (Unabridged)')]

            print('Filename: {}'.format(m_filename))
            print('Title: {}'.format(m_title))
            print('Artist: {}'.format(m_artist))
            print('Chapters: {}'.format(m_num_chapters))
            print()
            print('Decrypting and converting to MP3 [{}]...'
                  .format(tmp_cnv_filename))

            convert = subprocess.run(['ffmpeg', '-loglevel',
                                      'error', '-stats',
                                      '-activation_bytes', self.auth_code,
                                      '-i', self.aax_file, '-vn',
                                      '-codec:a', 'libmp3lame',
                                      '-codec:v', 'copy',
                                      '-ab', m_bit_rate,
                                      '-map_metadata', '-1',
                                      tmp_cnv_filename])

            if convert.returncode:
                raise Exception('An error occurred when running ffmpeg')

            print()
            print('Extracting chapters to individual files...')

            output_dir = re.sub('[\\/:"*?<>|]+', '-', '{}\\{}\\{}'
                                .format(self.base_dir,
                                        m_album_artist,
                                        m_title))

            os.makedirs(output_dir, exist_ok=True)

            c_track = 1

            for m_chapter in m_chapters:
                c_start = m_chapter['start_time']
                c_end = m_chapter['end_time']
                c_title = m_chapter['tags']['title']
                c_filename = re.sub('[\\/:"*?<>|]+',
                                    '-',
                                    '{}\\{:02d} - {}.mp3'
                                    .format(output_dir, c_track, c_title))

                print('Chapter {:02d} [{}] to {}'
                      .format(c_track, c_title, c_filename))

                chaptrack = subprocess.run(
                    ['ffmpeg', '-loglevel', 'error', '-stats',
                     '-i', tmp_cnv_filename,
                     '-codec:a', 'copy', '-codec:v', 'copy',
                     '-ss', c_start, '-to', c_end,
                     '-map_metadata', '-1',
                     '-id3v2_version', '3',
                     '-metadata', 'track={}'.format(c_track),
                     '-metadata', 'title={}'.format(c_title),
                     '-metadata', 'artist={}'.format(m_artist),
                     '-metadata', 'album_artist={}'.format(m_album_artist),
                     '-metadata', 'album={}'.format(m_title),
                     '-metadata', 'comment={}'.format(m_comment),
                     '-metadata', 'copyright={}'.format(m_copyright),
                     '-metadata', 'date={}'.format(m_date),
                     '-metadata', 'genre={}'.format(m_genre),
                     c_filename])

                c_track += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('auth_code', help='Audible authentication code')
    parser.add_argument('aax_file', help='Audible audiobook filename')
    parser.add_argument('-d', '--directory',
                        help='Output directory',
                        default='.')

    args = parser.parse_args()

    if args:
        aax_conv = AAXConverter(args.auth_code, args.aax_file, args.directory)

        aax_conv.convert_file()
    else:
        parser.print_help()
