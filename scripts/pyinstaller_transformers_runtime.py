"""
Light PyInstaller runtime hook for tokenizer native dependencies.

Do not import transformers here. Importing transformers during the runtime
hook slows down application startup.
"""

from importlib.metadata import PackageNotFoundError, version

import google.protobuf
import sentencepiece
import sentencepiece._sentencepiece


try:
    version("protobuf")
except PackageNotFoundError as error:
    raise RuntimeError(
        "protobuf metadata is missing from the frozen application. "
        'Add copy_metadata("protobuf") to autosubscriber_app.spec.'
    ) from error


try:
    version("sentencepiece")
except PackageNotFoundError as error:
    raise RuntimeError(
        "sentencepiece metadata is missing from the frozen application."
    ) from error


_PROTOBUF_MODULE = google.protobuf
_SENTENCEPIECE_MODULE = sentencepiece
_SENTENCEPIECE_NATIVE_MODULE = sentencepiece._sentencepiece