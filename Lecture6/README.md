# Lecture 4

1. Duplicate the `.env.example` file and rename it to `.env`.
2. Open the `.env` file and set the `OPENAI_API_KEY` variable with your OpenAI API key.
3. Install the required dependencies by running:

   ```bash
   pip install -r requirements.txt
   ```

- If you are using a virtual environment, make sure to activate it before running the above command.

4. Run the QDrant container by running the following command:

   ```bash
   docker compose up --build -d
   ```

5. For the first time, you need to create the QDrant collection, so set the `INSERT_CHUNKS` variable to `True` in the `main.py` file and run the following command:

   ```bash
   python main.py
   ```

6. Open the QDrant Dashboard by going to `http://localhost:6333/dashboard#/collections/TIC43` in your browser.

7. Once the collection is created, set the `INSERT_CHUNKS` variable to `False` in the `main.py` file and run the following command to start the application:

   ```bash
   python main.py
   ```

8. To evaluate the impact of the RAG context, set the `WITH_CONTEXT` variable to `False`  and run again the `main.py`. Verify if the answer is correct.
