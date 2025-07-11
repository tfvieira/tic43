# Lecture 9

1. Duplicate the `.env.example` file and rename it to `.env`.
2. Open the `.env` file and set the `OPENAI_API_KEY` and `BRAVE_API_KEY` variables with your OpenAI API key and Brave Search API key.
3. Install the required dependencies by running:

   ```bash
   pip install -r requirements.txt
   ```

- If you are using a virtual environment, make sure to activate it before running the above command.

4. Run the QDrant container by running the following command:

   ```bash
   docker compose up --build -d
   ```

5. Run the main.py file by running the following command:

   ```bash
   python main.py
   ```

   - Change the `INSERT_CHUNKS` and `WITH_CONTEXT` variables in the main.py file to `True` or `False` to enable or disable the insertion of chunks and the use of context.

6. Check the output in the created file.
