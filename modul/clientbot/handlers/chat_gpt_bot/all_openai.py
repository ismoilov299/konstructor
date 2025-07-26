from openai import OpenAI

client = OpenAI(api_key="")
#
OPENAI_COMPLETION_OPTIONS = {
    "temperature": 0.1,
    "max_tokens": 1000,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "timeout": 60.0,
}


class ChatGPT:
    user_contexts = {}

    def update_context(self, user_id, message):
        if user_id in self.user_contexts:
            self.user_contexts[user_id].append(message)
        else:
            self.user_contexts[user_id] = []
            self.user_contexts[user_id].append(message)

    def get_all_contexts(self, user_id):
        if user_id in self.user_contexts:
            result = self.user_contexts[user_id]
            return result
        return None

    def chat_gpt(self, user_id, message, gpt='gpt-4o', context=False):
        if context is False:

            try:
                response = client.chat.completions.create(
                    model=gpt,
                    messages=[{"role": "user", "content": message}],
                    **OPENAI_COMPLETION_OPTIONS
                )

                print(f'user_id: {user_id} send --> {message}\n'
                      f'assistant: {response.choices[0].message.content}')

                return response.choices[0].message.content

            except Exception as e:
                print(e)
        elif context is True:
            user_context = self.get_all_contexts(user_id)
            if user_context:

                var = user_context + [{"role": "user", "content": message}]

                response = client.chat.completions.create(
                    model=gpt,
                    messages=var,
                    **OPENAI_COMPLETION_OPTIONS
                )

                self.update_context(user_id, {"role": "user", "content": message})
                self.update_context(user_id, {"role": "assistant", "content": response.choices[0].message.content})

                print(f'user_id: {user_id} all_chat: {self.get_all_contexts(user_id)}')
                return response.choices[0].message.content

            else:
                try:
                    response = client.chat.completions.create(
                        model=gpt,
                        messages=[{"role": "user", "content": message}],
                        **OPENAI_COMPLETION_OPTIONS
                    )
                    self.update_context(user_id, {"role": "user", "content": message})
                    self.update_context(user_id, {"role": "assistant", "content": response.choices[0].message.content})

                    print(f'user_id: {user_id} start -- > {self.get_all_contexts(user_id)}')
                    return response.choices[0].message.content

                except:
                    return None



