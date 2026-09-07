import json
import sys
import traceback
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


# ==============================================================
# MODEL PATHS
# ==============================================================

INDIC_EN_MODEL_PATH = Path(
    r"C:\Users\Lenovo\.cache\huggingface\hub"
    r"\models--ai4bharat--indictrans2-indic-en-dist-200M"
    r"\snapshots\eb9e49d81077cfc5311e82ff36d8c1fc11557b5d"
)

EN_INDIC_MODEL_PATH = Path(
    r"C:\Users\Lenovo\.cache\huggingface\hub"
    r"\models--ai4bharat--indictrans2-en-indic-dist-200M"
    r"\snapshots\173b94239f7c38886b2747b8d4a5db771a7e1232"
)


# ==============================================================
# LANGUAGE HELPERS
# ==============================================================

def is_english(language: str) -> bool:
    return language == "eng_Latn"


def is_indic(language: str) -> bool:
    return language != "eng_Latn"


# ==============================================================
# MODEL LOADER
# ==============================================================

def load_model(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(
            f"IndicTrans2 model path does not exist: {model_path}"
        )

    print(
        f"Loading IndicTrans2 model from:\n{model_path}",
        file=sys.stderr,
        flush=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )

    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )

    model.eval()

    print(
        "IndicTrans2 model ready.",
        file=sys.stderr,
        flush=True,
    )

    return tokenizer, model


# ==============================================================
# TRANSLATION
# ==============================================================

def translate(
    text: str,
    source_language: str,
    target_language: str,
) -> str:

    # ----------------------------------------------------------
    # Select the correct IndicTrans2 checkpoint.
    #
    # Indic → English:
    #   indic-en-dist-200M
    #
    # English → Indic:
    #   en-indic-dist-200M
    # ----------------------------------------------------------

    if is_english(source_language) and is_indic(target_language):
        model_path = EN_INDIC_MODEL_PATH

    elif is_indic(source_language) and is_english(target_language):
        model_path = INDIC_EN_MODEL_PATH

    else:
        raise ValueError(
            "Unsupported offline translation direction: "
            f"{source_language} -> {target_language}. "
            "Offline IndicTrans2 currently supports "
            "English <-> Indic translation."
        )

    tokenizer, model = load_model(model_path)

    # IndicTrans2 expects the source and target language
    # codes at the beginning of the input.
    source_text = (
        f"{source_language} {target_language} {text}"
    )

    batch = tokenizer(
        [source_text],
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=256,
    )

    with torch.no_grad():
        generated = model.generate(
            **batch,
            max_length=256,
            num_beams=5,
        )

    result = tokenizer.batch_decode(
        generated,
        skip_special_tokens=True,
    )[0]

    return result.strip()


# ==============================================================
# STDIN REQUEST LOOP
# ==============================================================

for line in sys.stdin:

    line = line.strip()

    if not line:
        continue

    try:
        request = json.loads(line)

        text = request["text"]
        source_language = request["source_language"]
        target_language = request["target_language"]

        result = translate(
            text=text,
            source_language=source_language,
            target_language=target_language,
        )

        response = {
            "success": True,
            "translated_text": result,
            "source_language": source_language,
            "target_language": target_language,
        }

    except Exception as exc:

        response = {
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    print(
        json.dumps(
            response,
            ensure_ascii=False,
        ),
        flush=True,
    )