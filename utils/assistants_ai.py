from openai import OpenAI
from utils.more_func import json_loader

import time
import logging


class Assistants_AI:

    def __init__(self, openai_key: str = 'None', organization_key: str = 'None'):

        self.run = None
        self.assistant = None
        self.assistant_id = None
        self.message = None
        self.thread = None
        self.thread_id = None
        self.file = None
        self.file_id = None

        try:
            if openai_key:
                self.client = OpenAI(api_key=openai_key)
            elif organization_key:
                self.client = OpenAI(organization=organization_key)

        except Exception as e:
            return {"message": "Error creating OpenAI"}
    def can_run(self, input: str):
        try:
            response = self.client.moderations.create(
                input = input,
                timeout=10,
            )
            return not any([moder.flagged for moder in response.results])
        except Exception as e:
            raise Exception(f"OpenAI не ответил на запрос. Попробуйте позже. (Звездочки вернулись) ({e})")
        
    # ____Генератор текста для презентаций_____
    def generator(self):
        try:
            self.assistant = self.client.beta.assistants.create(
                name="GeneratorPresent",
                instructions='You are an artificial intelligence that should create text for presentations. Your task is to return the text in JSON format in a strictly specified example:'
                             '{"page1": {"title": "Title of page 1","content": "Content of page 1"}, "page2": {"title": "Title of page 2","content": "Content of page 2"}}'
                             'The number of pages and the subject will be specified upon request !Give full answers and do not shorten it!',
                model="gpt-3.5-turbo"
            )
            self.assistant_id = self.assistant.id

            return self.assistant

        except Exception as e:

            return {"message": "Error creating OpenAI"}

    def add_file(self, filename):
        print(filename)
        self.file = self.client.files.create(
            file=open(f"media/{filename}", "rb"),
            purpose='assistants'
        )

        self.file_id = self.file.id

    def create_assistant(self, name: str, instructions: str, model: str = "gpt-3.5-turbo"):
        try:

            self.assistant = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=model
            )

            self.assistant_id = self.assistant.id

            return self.assistant

        except Exception as e:

            return {"message": "Error creating OpenAI"}

    def add_thread(self):
        try:
            self.thread = self.client.beta.threads.create()

            self.thread_id = self.thread.id

        except Exception as e:
            print(3)

    def add_message(self, message):
        try:

            self.message = self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=message
            )

        except Exception as e:
            print(4)

    def run_programmer(self):
        try:
            self.run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
            )

        except Exception as e:
            print(e)

    def check_status_run(self):
        while True:
            try:
                run = self.client.beta.threads.runs.retrieve(thread_id=self.thread_id, run_id=self.run.id)
                if run.completed_at:
                    elapsed_time = run.completed_at - run.created_at
                    formatted_elapsed_time = time.strftime(
                        "%H:%M:%S", time.gmtime(elapsed_time)
                    )
                    print(f"Run completed in {formatted_elapsed_time}")
                    logging.info(f"Run completed in {formatted_elapsed_time}")

                    # Get messages here once Run is completed!

                    messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)
                    last_message = messages.data[0]
                    response = last_message.content[0].text.value
                    return response

            except Exception as e:

                logging.error(f"An error occurred while retrieving the run: {e}")

                break

            logging.info("Waiting for run to complete...")
            time.sleep(5)

    def steps_logs(self):
        try:
            run_steps = self.client.beta.threads.runs.steps.list(thread_id=self.thread_id, run_id=self.run.id)
            print(f"Steps---> {run_steps.data[0]}")

        except Exception as e:
            print(e)
