from __future__ import print_function
import os
import re
import os.path
import glob
import tempfile
import shutil
import yaml
import io

# For backwards compatibility, remove in bright and shiny future.
def detect_version(problemdir, problemtex):
    # Check for 0.1 - lack of \problemname
    if open(problemtex).read().find('\problemname') < 0:
        return '0.1'
    return ''  # Current


class Template:
    def __init__(self, problemdir, language='',
                 title='Problem Title', force_copy_cls=False):
        if not os.path.isdir(problemdir):
            raise Exception('%s is not a directory' % problemdir)

        if problemdir[-1] == '/':
            problemdir = problemdir[:-1]
        stmtdir = os.path.join(problemdir, 'problem_statement')

        langs = []
        if glob.glob(os.path.join(stmtdir, 'problem.tex')):
            langs.append('')
        for f in glob.glob(os.path.join(stmtdir, 'problem.[a-z][a-z].tex')):
            langs.append(re.search("problem.([a-z][a-z]).tex$", f).group(1))
        if len(langs) == 0:
            raise Exception('No problem statements available')

        dotlang = ''
        # If language unspec., use first available one (will be
        # problem.tex if exists)
        if language == '':
            language = langs[0]
        if language != '':
            if len(language) != 2 or not language.isalpha():
                raise Exception('Invalid language code "%s"' % language)
            if language not in langs:
                raise Exception('No problem statement for language "%s" available' % language)
            dotlang = '.' + language

        # Used in the template.tex variable substitution.
        self.language = dotlang
        problemtex = os.path.join(stmtdir, 'problem' + dotlang + '.tex')

        if not os.path.isfile(problemtex):
            raise Exception('Unable to find problem statement, was looking for "%s"' % problemtex)
        
        self.templatefile = 'template.tex'
        self.clsfile = 'problemset.cls'
        timelim = 1  # Legacy for compatibility with v0.1
        version = detect_version(problemdir, problemtex)
        if version != '':
            print('Note: problem is in an old version (%s) of problem format, you should consider updating it' % version)
            self.templatefile = 'template_%s.tex' % version
            self.clsfile = 'problemset_%s.cls' % version

        templatepaths = [os.path.join(os.path.dirname(__file__), 'templates/latex'),
                         os.path.join(os.path.dirname(__file__), '../templates/latex'),
                         '/usr/lib/problemtools/templates/latex']
        self.templatepath = next((p for p in templatepaths
                                  if os.path.isdir(p) and os.path.isfile(os.path.join(p, self.templatefile))),
                                 None)
        if self.templatepath is None:
            raise Exception('Could not find directory with latex template "%s"' % self.templatefile)

        self.basedir = os.path.dirname(problemdir)
        self.shortname = os.path.basename(problemdir)
        sample_dir = os.path.join(problemdir, 'data', 'sample')
        self.samples = sorted(set([os.path.splitext(os.path.basename(f))[0]
                                   for f in (glob.glob(os.path.join(sample_dir, '*.in')) +
                                             glob.glob(os.path.join(sample_dir, '*.interaction')))]))
        self.problemset_cls = os.path.join(self.basedir, 'problemset.cls')

        self.copy_cls = True
        if os.path.isfile(self.problemset_cls) and not force_copy_cls:
            print('%s exists, will not copy it -- in case of weirdness this is likely culprit' % self.problemset_cls)
            self.copy_cls = False

        # Localize strings from templates/latex/strings.yaml
        with open(os.path.join(self.templatepath, 'strings.yaml'), 'r') as stringfile:
            self.strings = yaml.load(stringfile)


    def __enter__(self):
        if self.copy_cls:
            shutil.copyfile(os.path.join(self.templatepath, self.clsfile), self.problemset_cls)

        (templfd, self.filename) = tempfile.mkstemp(suffix='.tex', dir=self.basedir)
        templout = io.open(templfd, 'w', encoding = 'utf8')
        templin = open(os.path.join(self.templatepath, self.templatefile))
        data = {'language': self.language,
                'shortname': self.shortname}
        if self.language in self.strings:
            strings = self.strings[self.language]
        else:
            strings = self.strings['.en']
            print('Unable to find string translations into {}, using English instead'.format(self.language))
        for s in strings:
            data[s] = strings[s]
        for line in templin:
            try:
                templout.write(unicode(line % data))
            except:
                # This is a bit ugly I guess
                for sample in self.samples:
                    data['sample'] = sample
                    templout.write(unicode(line % data))
                if self.samples:
                    del data['sample']
        templout.close()
        templin.close()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.problemset_cls is not None and self.copy_cls and  os.path.isfile(self.problemset_cls):
            os.remove(self.problemset_cls)
        if self.filename is not None:
            for f in glob.glob(os.path.splitext(self.filename)[0] + '.*'):
                if os.path.isfile(f):
                    os.remove(f)

    def get_file_name(self):
        assert os.path.isfile(self.filename)
        return self.filename
