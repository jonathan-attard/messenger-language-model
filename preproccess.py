"""
Message by someone$
Message by me£

"""
import os
import json

END_QUERY = '$'
END_RESPONSE = '£'
END_CONVERSATION = '¬'

SPECIAL_CHARS = [END_QUERY, END_RESPONSE, END_CONVERSATION]

names_file_path = "data/track_names.txt"
messages_dir = "data/messages/inbox"
messages_out_file = "data/messages.txt"

skip_user_keyword = "facebookuser"

track_names = list()

with open(names_file_path, "r") as f_name:
    for line in f_name.readlines():
        if len(line) > 1:
            line = line.replace("\n", "")
            track_names.append(line)

with open(messages_out_file, "w", encoding="utf-8") as out:
    for chat_dir in os.listdir(messages_dir):
        messages_file_names = sorted([f for f in os.listdir(os.path.join(messages_dir, chat_dir)) if
                                      f.startswith("message_") and f.endswith(".json") and skip_user_keyword not in f], reverse=True)
        for f_name in messages_file_names:
            message_path = os.path.join(messages_dir, chat_dir, f_name)
            with open(message_path, "r", encoding="utf-8") as f:
                message_dict = json.load(f)
                messages = message_dict["messages"]
                messages.sort(key=lambda x: x["timestamp_ms"])

                for message in messages:
                    if "content" in message:
                        content = message["content"]

                        # Removing special characters
                        for k in SPECIAL_CHARS:
                            content.replace(k, "")

                        # Marking end of message
                        if message["sender_name"] in track_names:
                            content += END_RESPONSE
                        else:
                            content += END_QUERY

                        out.write(content)

        # Marking end of conversation
        out.write(END_CONVERSATION)
