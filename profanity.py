from better_profanity import profanity
import os

base_dir = "data/profanity"

profanity.load_censor_words()
custom_badwords = list()

file_names = os.listdir(base_dir)
for f_name in file_names:
    lang_name = os.path.splitext(f_name)[0]
    with open(os.path.join(base_dir, f_name), "r") as f:
        custom_badwords.extend(f.read().lower().split("\n"))

profanity.add_censor_words(custom_badwords)

if __name__ == "__main__":
    text = "You p1ec3 of sHit. cum. Goxx. Happy"
    censored_text = profanity.censor(text)
    print(censored_text)
    # You **** of ****.
