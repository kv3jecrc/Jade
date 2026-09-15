# LoRA vs QLoRA Fine-Tuning — TinyLlama-1.1B-Chat

`lora_qlora_finetuning.ipynb` fine-tunes **TinyLlama/TinyLlama-1.1B-Chat-v1.0**
(a 1.1B-parameter, LLaMA-architecture, instruction-tuned model) two ways —
LoRA and QLoRA — under identical hyperparameters, and compares them.

## Why TinyLlama-1.1B-Chat

It's Apache-2.0 licensed (no gated-access approval wait like
`meta-llama/*` checkpoints require), genuinely LLaMA-architecture, ~1.1B
parameters, and already instruction-tuned — so it satisfies the "1B
LLaMA-based instruction model" requirement and can be run in a single
Colab session without any access-request delay. Swap `MODEL_NAME` in the
notebook for `meta-llama/Llama-3.2-1B-Instruct` if you have approved
access to it; nothing else needs to change.

## How to run

1. Open the notebook in Google Colab.
2. **Runtime → Change runtime type → T4 GPU** (QLoRA's 4-bit loading
   requires a CUDA GPU — `bitsandbytes` doesn't support 4-bit on CPU).
3. Run all cells top to bottom.

If Colab isn't accessible, run it locally in Jupyter on any machine with
a CUDA-capable GPU — the notebook has no Colab-specific code beyond the
`!pip install` cell, which works identically in local Jupyter.

## What it does

1. **LoRA**: loads the base model in fp16 with all weights frozen, adds
   LoRA adapters (`r=8`, `lora_alpha=16`) only to `q_proj` and `v_proj`,
   trains for 2 epochs at `lr=2e-4` on a small embedded instruction
   dataset, and records trainable parameter count, final training loss,
   and peak GPU memory.
2. **QLoRA**: reloads the base model in 4-bit NF4 quantized format via
   `bitsandbytes`, runs `prepare_model_for_kbit_training`, attaches the
   *same* LoRA config, trains under identical settings, and records the
   same three metrics.
3. Generates responses for the same 3 test prompts from both fine-tuned
   models and prints them side by side, plus a results table (trainable
   params, total params, % trainable, final loss, peak GPU memory,
   runtime) comparing the two runs.
4. Ends with a markdown "Observations" template — filled in after running,
   since the actual numbers/qualitative comparison depend on your run.

## Note

The dataset embedded in the notebook is a small (16-example) synthetic
instruction set, chosen deliberately to keep the run fast and reliable on
a free-tier GPU. Swap `TRAIN_EXAMPLES` for a real dataset (e.g.
`databricks/databricks-dolly-15k` via `datasets.load_dataset`) for a more
substantive fine-tuning result — the LoRA/QLoRA/training/measurement
pipeline itself is unaffected either way.
