import functions_framework
import os
import json

# Note: The actual DPO training libraries (torch, transformers, etc.)
# should be listed in the accompanying 'requirements.txt' file.

@functions_framework.http
def dpo_training_handler(request):
    """
    HTTP Cloud Function to trigger a DPO training job.
    Receives user_id and training_data from the main backend.
    """
    # --- 1. Parse and Validate Request ---
    if request.method != 'POST':
        return 'This function only accepts POST requests.', 405

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            raise ValueError("Invalid JSON")
            
        user_id = request_json.get('user_id')
        username = request_json.get('username')
        training_data = request_json.get('training_data')

        if not all([user_id, username, training_data]):
            raise ValueError("Missing user_id, username, or training_data in request body")

    except ValueError as e:
        print(f"Error parsing request: {e}")
        return f"Bad Request: {e}", 400

    print(f"Received training request for user '{username}' (ID: {user_id}).")
    print(f"Number of preference pairs: {len(training_data)}")

    # --- 2. Execute DPO Training ---
    # This is where you would insert your DPO training script.
    # The 'training_data' variable is a list of dicts, with each dict
    # containing 'prompt', 'chosen', and 'rejected' keys.
    
    try:
        # =================================================================
        # TODO: INSERT YOUR DPO TRAINING LOGIC HERE
        #
        # Example steps:
        # 1. Load a base model (e.g., from Hugging Face).
        # 2. Prepare the dataset from the 'training_data' list.
        # 3. Configure and run the DPO trainer from the 'trl' library.
        # 4. Save the fine-tuned LoRA adapter to Google Cloud Storage.
        #
        # IMPORTANT:
        # Cloud Functions have a maximum timeout (up to 60 minutes for 2nd Gen).
        # If your training takes longer, you should use this function to trigger
        # a more robust, long-running job on Vertex AI Training or a GCE VM
        # instead of running the training directly inside the function.
        # =================================================================
        
        print("Starting placeholder for DPO training logic...")
        
        # Placeholder: Simulate a training process
        # In a real scenario, this part would involve torch, transformers, etc.
        final_model_path = f"gs://mlops-compute-lab-dpo-models/dpo_models/{username}_{user_id}/lora/"
        print(f"Placeholder: Training complete. Model would be saved to {final_model_path}")

        # --- 3. Return Response ---
        # Return a success message. The main application is not waiting for this,
        # but it's good practice for logging and debugging.
        response_message = {
            "status": "success",
            "message": f"Training job for user {username} completed successfully (placeholder).",
            "model_path": final_model_path
        }
        
        # The main app that called this function has a short timeout and expects a 202.
        # However, for logging purposes, we return a 200 when the sync process is done.
        return json.dumps(response_message), 200

    except Exception as e:
        # Log the full error for debugging
        print(f"An error occurred during the training process: {e}")
        
        # Return a server error response
        return "Internal Server Error: Training failed.", 500
