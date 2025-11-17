# 🚀 Lambda Labs A100 Fine-tuning Setup Guide

Complete guide to fine-tune Llama 3.2 3B on Lambda Labs A100 GPU

**Expected Cost: $0.83 - $1.10**
**Expected Time: 45-60 minutes**

---

## 📋 Table of Contents
1. [Account Setup](#1-account-setup)
2. [Launch A100 Instance](#2-launch-a100-instance)
3. [Upload Training Data](#3-upload-training-data)
4. [Run Fine-tuning](#4-run-fine-tuning)
5. [Download Model](#5-download-model)
6. [Cleanup](#6-cleanup)
7. [Troubleshooting](#troubleshooting)

---

## 1. Account Setup

### Step 1.1: Create Lambda Labs Account
1. Go to [cloud.lambdalabs.com](https://cloud.lambdalabs.com)
2. Click **"Sign Up"**
3. Complete registration with email verification

### Step 1.2: Add Credits
1. Navigate to **"Account" → "Billing"**
2. Click **"Add Credits"**
3. Add **$10-20** (recommended for testing)
   - A100 40GB: $1.10/hour
   - Minimum $10 for first-time users
4. Payment methods: Credit card, wire transfer

### Step 1.3: SSH Key Setup (Important!)
1. Go to **"Account" → "SSH Keys"**
2. Click **"+ Add SSH Key"**
3. **On your local machine**, generate SSH key if you don't have one:
   ```bash
   # macOS/Linux:
   ssh-keygen -t ed25519 -C "your_email@example.com"

   # Press Enter to accept default location
   # Press Enter twice to skip passphrase (or set one)
   ```
4. Copy your public key:
   ```bash
   # macOS/Linux:
   cat ~/.ssh/id_ed25519.pub

   # Copy the entire output
   ```
5. Paste into Lambda Labs SSH Key field
6. Name it (e.g., "MacBook Pro")
7. Click **"Add SSH Key"**

---

## 2. Launch A100 Instance

### Step 2.1: Launch Instance
1. Go to **"Instances"** → **"Launch Instance"**
2. Select GPU: **A100 (40 GB SXM4)**
   - Price: $1.10/hour
   - Availability: Check multiple regions
3. Select Region: Choose any available (e.g., us-west-1, us-east-1)
4. Select File System: **"Don't attach a filesystem"** (for simple usage)
5. Click **"Launch Instance"**

⚠️ **Note:** A100 instances can be in high demand. If unavailable:
- Try different regions
- Check back every few hours
- Consider RTX 6000 Ada ($0.75/hr) as alternative

### Step 2.2: Wait for Instance to Start
- Status will change from "booting" → "running" (1-2 minutes)
- Note the **IP address** (e.g., 150.136.123.45)

### Step 2.3: SSH into Instance
```bash
# Connect to your instance
ssh ubuntu@<YOUR_IP_ADDRESS>

# Example:
ssh ubuntu@150.136.123.45
```

First-time connection will ask to confirm fingerprint - type `yes`

### Step 2.4: Verify GPU
```bash
# Check GPU is available
nvidia-smi

# Should show:
# - NVIDIA A100-SXM4-40GB
# - CUDA Version: 12.x
# - GPU Memory: 40960 MiB
```

---

## 3. Upload Training Data

### Step 3.1: Start JupyterLab
```bash
# On the Lambda instance:
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

Copy the token URL shown (e.g., `http://127.0.0.1:8888/lab?token=abc123...`)

### Step 3.2: SSH Tunnel (On Your Local Machine)
**Open a NEW terminal window** on your local machine:

```bash
# Create SSH tunnel for Jupyter
ssh -N -L 8888:localhost:8888 ubuntu@<YOUR_IP_ADDRESS>

# Example:
ssh -N -L 8888:localhost:8888 ubuntu@150.136.123.45
```

This will appear to hang - that's normal! Keep it running.

### Step 3.3: Access JupyterLab
1. Open browser: `http://localhost:8888`
2. Paste the token from Step 3.1 if asked
3. You should see JupyterLab interface

### Step 3.4: Upload Notebook
1. In JupyterLab, click **Upload** button (up arrow icon)
2. Navigate to your local: `data_pipeline/lambda_finetune_llama3b.ipynb`
3. Upload the file

### Step 3.5: Upload Training Data

**Option A: Upload via JupyterLab (Recommended)**
1. Create `data` folder in JupyterLab
2. Click **Upload** button
3. Upload these files from `data_pipeline/data/synthetic/processed/`:
   - `recipes_train_chat.jsonl` (13 MB)
   - `recipes_val_chat.jsonl` (1.7 MB)
4. Move them into `data/` folder

**Option B: Upload via SCP (Faster for large files)**

On your local machine (NEW terminal):
```bash
# Navigate to your data directory
cd ~/Desktop/Jun/MLOps/PantryPilot/data_pipeline/data/synthetic/processed/

# Upload training data
scp recipes_train_chat.jsonl ubuntu@<YOUR_IP>:~/data/
scp recipes_val_chat.jsonl ubuntu@<YOUR_IP>:~/data/

# Example:
scp recipes_train_chat.jsonl ubuntu@150.136.123.45:~/data/
scp recipes_val_chat.jsonl ubuntu@150.136.123.45:~/data/
```

---

## 4. Run Fine-tuning

### Step 4.1: Open Notebook
1. In JupyterLab, click on `lambda_finetune_llama3b.ipynb`
2. Notebook will open

### Step 4.2: Run Cells in Order

**Cell 1: Install Dependencies** (~2 minutes)
```python
!pip install -q transformers==4.57.1 peft==0.18.0 ...
```

**Cell 2: Check GPU** (~5 seconds)
```python
!nvidia-smi
```
Verify A100 is detected

**Cell 3: HuggingFace Login** (~5 seconds)
```python
HF_TOKEN = "your_huggingface_token_here"  # Get from https://huggingface.co/settings/tokens
login(token=HF_TOKEN)
```

**Cell 4: Verify Data Files** (~1 second)
Should show:
```
✅ Training data found!
-rw-r--r-- 1 ubuntu ubuntu  13M recipes_train_chat.jsonl
-rw-r--r-- 1 ubuntu ubuntu 1.7M recipes_val_chat.jsonl
```

**Cell 5-6: Load Dataset** (~10 seconds)
Loads and previews training data

**Cell 7-8: Load Model** (~2-3 minutes)
Downloads Llama 3.2 3B model (6.4 GB)

**Cell 9: Apply LoRA** (~5 seconds)
Should show: `trainable params: 9,175,040 || trainable%: 0.2848`

**Cell 10-11: Setup Training** (~5 seconds)
Should show:
```
Train samples: 9,594
Val samples: 1,197
Total training steps: 1,799
⏱️ Estimated time: 45-60 minutes
💰 Estimated cost: $0.83 - $1.10
```

**Cell 12: START TRAINING** (~45-60 minutes) 🚀
```python
trainer.train()
```

**What to expect:**
- First few steps will be slow (compilation)
- Speed should stabilize at **0.5-0.8 it/s**
- Progress bar will update every 10 steps
- Validation runs every 100 steps
- Training loss should decrease over time

**Example output:**
```
Step    Training Loss    Validation Loss
10      2.145            -
20      1.987            -
100     1.654            1.702
200     1.423            1.458
...
1799    0.892            0.945
✅ Training complete!
```

### Step 4.3: Monitor Progress
You can monitor in real-time:
- Progress bar shows steps/time remaining
- Training loss logged every 10 steps
- Validation loss every 100 steps
- TensorBoard available (optional)

---

## 5. Download Model

### Step 5.1: Save Model (~30 seconds)
Run the save cells in notebook:
```python
trainer.save_model("./llama3b_recipe_lora_final")
```

### Step 5.2: Test Model (~1 minute)
Run test cells to verify model works:
```python
# Should generate Korean and vegan recipes
```

### Step 5.3: Zip Model (~30 seconds)
```python
!zip -r llama3b_recipe_lora_final.zip llama3b_recipe_lora_final/
```

### Step 5.4: Download Model

**Option A: JupyterLab Download**
1. Right-click `llama3b_recipe_lora_final.zip` in file browser
2. Click **"Download"**
3. Save to your local machine

**Option B: SCP Download (Faster)**

On your local machine:
```bash
# Download the model
scp ubuntu@<YOUR_IP>:~/llama3b_recipe_lora_final.zip ~/Desktop/

# Example:
scp ubuntu@150.136.123.45:~/llama3b_recipe_lora_final.zip ~/Desktop/
```

---

## 6. Cleanup

### ⚠️ IMPORTANT: Stop Instance to Avoid Charges!

### Step 6.1: Terminate Instance
1. Go to Lambda Labs dashboard
2. Click **"Instances"**
3. Find your running instance
4. Click **"Terminate"**
5. Confirm termination

**Cost is charged per second**, so terminate as soon as you download the model!

### Step 6.2: Verify Termination
- Instance status should show "terminated"
- Billing will stop immediately

### Step 6.3: Cost Summary
Check your actual cost:
1. Go to **"Account" → "Billing"**
2. View recent usage
3. Should be around **$0.83 - $1.10** for 45-60 minutes

---

## 7. Use Model Locally

### Step 7.1: Extract Model
```bash
unzip llama3b_recipe_lora_final.zip
cd llama3b_recipe_lora_final
```

### Step 7.2: Load Model in Python
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.2-3B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")

# Load LoRA adapter
model = PeftModel.from_pretrained(base_model, "./llama3b_recipe_lora_final")
model.eval()

# Generate recipe
prompt = """<|im_start|>system
You are a recipe generation AI that creates recipes based on user inventory and preferences.<|im_end|>
<|im_start|>user
I have chicken, rice, and soy sauce. I want a Korean recipe.<|im_end|>
<|im_start|>assistant
"""

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response)
```

---

## Troubleshooting

### Problem: "No A100 instances available"
**Solution:**
- Try different regions (us-west-1, us-east-1, europe-west-1)
- Check back every few hours (instances become available)
- Consider alternative: RTX 6000 Ada ($0.75/hr, 48GB)
- Use email notification when instances available

### Problem: "SSH connection refused"
**Solution:**
1. Wait 1-2 minutes after launch (instance still booting)
2. Check IP address is correct
3. Verify SSH key was added to account
4. Try: `ssh -v ubuntu@<IP>` for debug info

### Problem: "Permission denied (publickey)"
**Solution:**
1. Verify SSH key added to Lambda account
2. Check key is loaded: `ssh-add -l`
3. Add key manually: `ssh-add ~/.ssh/id_ed25519`
4. Regenerate and re-add SSH key

### Problem: "CUDA out of memory"
**Solution:**
1. Reduce batch size in notebook:
   ```python
   per_device_train_batch_size=4,  # Change from 8
   ```
2. Reduce max_length:
   ```python
   max_length=512,  # Change from 1024
   ```

### Problem: "Training very slow (< 0.1 it/s)"
**Solution:**
1. Check GPU is being used: `nvidia-smi` in terminal
2. Verify gradient checkpointing disabled:
   ```python
   gradient_checkpointing=False
   ```
3. Ensure FP16 enabled:
   ```python
   fp16=True
   ```

### Problem: "Cannot access JupyterLab"
**Solution:**
1. Check SSH tunnel is running (Step 3.2)
2. Verify port 8888: `http://localhost:8888` (not the IP)
3. Check JupyterLab token is correct
4. Restart JupyterLab:
   ```bash
   # Kill existing
   pkill -f jupyter

   # Restart
   jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
   ```

### Problem: "HuggingFace authentication failed"
**Solution:**
1. Verify your token is correct (get from https://huggingface.co/settings/tokens)
2. Check Llama 3.2 access approved at huggingface.co
3. Try manual login:
   ```python
   from huggingface_hub import notebook_login
   notebook_login()
   ```

### Problem: "Instance terminated but still charged"
**Solution:**
- Billing stops within 1 minute of termination
- Check "Billing" page for final charges
- Contact Lambda support if issues persist

---

## 💡 Tips & Best Practices

### Cost Optimization
- ✅ Terminate instance immediately after download
- ✅ Use smaller dataset for testing first
- ✅ Monitor training progress - stop if loss plateaus
- ✅ Set max_steps=500 for quick testing run

### Speed Optimization
- ✅ Use batch_size=8 on A100 40GB
- ✅ Disable gradient checkpointing
- ✅ Use FP16 mixed precision
- ✅ Set dataloader_num_workers=4

### Data Management
- ✅ Upload data via SCP (faster than JupyterLab)
- ✅ Download model via SCP (faster for large files)
- ✅ Keep backup of training data locally

### Monitoring
- ✅ Check `nvidia-smi` to verify GPU usage
- ✅ Monitor training loss - should decrease
- ✅ Run validation to check overfitting
- ✅ Use TensorBoard for detailed metrics

---

## 📚 Additional Resources

- **Lambda Labs Docs**: [docs.lambdalabs.com](https://docs.lambdalabs.com)
- **Lambda Labs Status**: [status.lambdalabs.com](https://status.lambdalabs.com)
- **HuggingFace PEFT**: [huggingface.co/docs/peft](https://huggingface.co/docs/peft)
- **Llama 3.2 Model**: [huggingface.co/meta-llama/Llama-3.2-3B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)

---

## 📞 Support

**Lambda Labs Support:**
- Email: support@lambdalabs.com
- Slack: [Lambda community](https://lambdalabs.com/community)

**PantryPilot Issues:**
- GitHub: Your project repository
- Questions: Open an issue

---

## ✅ Quick Start Checklist

Before starting, make sure you have:

- [ ] Lambda Labs account created
- [ ] $10-20 credits added
- [ ] SSH key added to account
- [ ] A100 instance launched and running
- [ ] JupyterLab accessible via SSH tunnel
- [ ] Training data uploaded (recipes_train_chat.jsonl, recipes_val_chat.jsonl)
- [ ] Notebook uploaded (lambda_finetune_llama3b.ipynb)
- [ ] HuggingFace token ready

Ready to train? Start at **Section 4: Run Fine-tuning**!

---

**Good luck with your fine-tuning! 🚀**
