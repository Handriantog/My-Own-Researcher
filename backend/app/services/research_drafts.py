"""Local extraction only. Abandoned drafts expire after seven days."""
import re
import shutil
import time
import uuid
from pathlib import Path
from ..utils.file_parser import FileParser
from ..services.text_processor import TextProcessor
from .research_storage import research_root, atomic_json, read_json, file_lock


class ResearchDrafts:
    RETENTION_SECONDS = 7*24*60*60

    def __init__(self, root=None):
        self.root = research_root(root) / 'drafts'
        self.root.mkdir(exist_ok=True)

    def folder(self, draft_id):
        if not isinstance(draft_id,str) or not re.fullmatch(r'draft_[a-f0-9]{32}',draft_id):
            raise ValueError('Invalid draft ID')
        return self.root / draft_id

    def get(self, draft_id):
        value = read_json(self.folder(draft_id) / 'draft.json')
        if not value or (not value.get('run_id') and value['expires_at'] < time.time()):
            raise LookupError('Draft expired or not found. Please add your sources again.')
        return value

    def text(self, draft_id):
        self.get(draft_id)
        return (self.folder(draft_id) / 'source.txt').read_text()

    @staticmethod
    def public(draft):
        return {key:draft[key] for key in ('draft_id','question','files','text_length','created_at','expires_at','run_id') if key in draft}

    def attach(self, draft_id, run_id):
        with file_lock(self.root / 'drafts.lock'):
            draft = self.get(draft_id)
            if draft.get('run_id') and draft['run_id'] != run_id:
                raise ValueError('This draft already has a research run')
            draft['run_id'] = run_id
            atomic_json(self.folder(draft_id) / 'draft.json',draft)

    def create(self, files, question):
        if not isinstance(question,str) or not question.strip() or len(question)>20000:
            raise ValueError('Enter a research question (up to 20,000 characters)')
        if not files or len(files)>20:
            raise ValueError('Add between 1 and 20 source files')
        with file_lock(self.root / 'drafts.lock'):
            self._expire()
            draft_id = 'draft_' + uuid.uuid4().hex
            folder = self.folder(draft_id)
            folder.mkdir()
            try:
                summaries, texts = [], []
                for index, file in enumerate(files):
                    filename = Path(file.filename or '').name
                    if not FileParser.is_supported(filename):
                        raise ValueError('Sources must be PDF, Markdown or text files')
                    target = folder / (str(index)+Path(filename).suffix.lower())
                    file.save(target)
                    try:
                        text = TextProcessor.preprocess_text(FileParser.extract_text(str(target))).strip()
                    except Exception:
                        raise ValueError(f'Cannot extract readable text from {filename}') from None
                    if not text:
                        raise ValueError(f'{filename} is empty or contains no readable text')
                    texts.append(text)
                    summaries.append({'filename':filename, 'size':target.stat().st_size,'characters':len(text)})
                text = '\n\n'.join(texts)
                (folder / 'source.txt').write_text(text)
                draft = {'draft_id':draft_id,'question':question.strip(),'files':summaries,
                         'text_length':len(text),'created_at':time.time(),
                         'expires_at':time.time()+self.RETENTION_SECONDS}
                atomic_json(folder / 'draft.json',draft)
                return draft
            except BaseException:
                shutil.rmtree(folder)
                raise

    def _expire(self):
        for path in self.root.glob('draft_*'):
            data = read_json(path / 'draft.json', {})
            if data and not data.get('run_id') and data.get('expires_at',0)<time.time():
                shutil.rmtree(path)
