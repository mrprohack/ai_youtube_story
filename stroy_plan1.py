from groq import Groq
import time
import os
from dotenv import load_dotenv


load_dotenv()
client = Groq(
    # This is the default and can be omitted
    api_key = os.getenv("GROQ_API_KEY"),
)

model = "llama-3.2-90b-vision-preview"

def save_introduction(book_name):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content" : open("system_prompt.txt", "r").read()
            },
            {
                "role": "user",
                "content": f"Write an introduction for book name :{book_name}",
            }
        ],
        model=model,
    )
    with open(book_name + "/" + "introduction.txt", "w") as f:
        f.write(chat_completion.choices[0].message.content)


def save_summary(book_name, summary, number):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content" : open("system_prompt.txt", "r").read()
            },
            {
                "role": "user",
                "content": book_name,
            },
            {
                "role": "assistant",
                "content": summary
            },{
                "role": "user",
                "content": f"Create an captivating script for the book '{book_name}' focusing on the {number}th title. Incorporate an engaging tone and weave a compelling story that draws the reader in. Begin the script with the title name and craft a narrative that explores the themes and emotions evoked by the title, using descriptive language to bring the story to life."
            }
        ],
        model=model,
    )
    with open(book_name + "/" + "title_" + str(number) + ".txt", "w") as f:
        f.write(str(chat_completion.choices[0].message.content))

def how_many_titles(book_name):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content" : "you are a helpful assistant"
            },
            {
                "role": "user",
                "content": f"how many title in the book {book_name} return a number only ",
            }
        ],
        model=model,
    )
    return chat_completion.choices[0].message.content

if __name__ == "__main__":
    # craete a folder the name of the book
    book_name = input("Enter the name of the book: ")
    if os.path.exists(book_name):
        print("\033[91m" + "folder already exists" + "\033[0m")
        exit()
    else:
        try:
            os.makedirs(book_name, exist_ok=True)
            print("\033[92m" + "folder created" + "\033[0m")
        except Exception as e:
            print("\033[91mError creating folder:\033[0m", e)
    save_introduction(book_name)
    print("\033[92m" + "introduction saved" + "\033[0m")
    summary = open(book_name + "/" + "introduction.txt", "r").read()
    max_titales = how_many_titles(book_name)
    print(f"\033[92mThere are {max_titales} titles in the book\033[0m")
    for i in range(1, int(max_titales) + 1):
        save_summary(book_name,summary, i)
        print(f"\033[92mTitle {i} saved\033[0m", end="\r")
        time.sleep(10)
