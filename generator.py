import tensorflow as tf
import numpy as np
import os
import time
from train import *
from preproccess import SPECIAL_CHARS, END_RESPONSE, END_QUERY

latest = tf.train.latest_checkpoint(checkpoint_dir)

# Load the previously saved weights
model.load_weights(latest)


class OneStep(tf.keras.Model):
    def __init__(self, model, chars_from_ids, ids_from_chars, temperature=1.0):
        super().__init__()
        self.temperature = temperature
        self.model = model
        self.chars_from_ids = chars_from_ids
        self.ids_from_chars = ids_from_chars

        # Create a mask to prevent "[UNK]" from being generated.
        skip_ids = self.ids_from_chars(['[UNK]'])[:, None]
        sparse_mask = tf.SparseTensor(
            # Put a -inf at each bad index.
            values=[-float('inf')] * len(skip_ids),
            indices=skip_ids,
            # Match the shape to the vocabulary
            dense_shape=[len(ids_from_chars.get_vocabulary())])
        self.prediction_mask = tf.sparse.to_dense(sparse_mask)

    @tf.function
    def generate_one_step(self, inputs, states=None):
        # Convert strings to token IDs.
        input_chars = tf.strings.unicode_split(inputs, 'UTF-8')
        input_ids = self.ids_from_chars(input_chars).to_tensor()

        # Run the model.
        # predicted_logits.shape is [batch, char, next_char_logits]
        predicted_logits, states = self.model(inputs=input_ids, states=states,
                                              return_state=True)
        # Only use the last prediction.
        predicted_logits = predicted_logits[:, -1, :]
        predicted_logits = predicted_logits / self.temperature
        # Apply the prediction mask: prevent "[UNK]" from being generated.
        predicted_logits = predicted_logits + self.prediction_mask

        # Sample the output logits to generate token IDs.
        predicted_ids = tf.random.categorical(predicted_logits, num_samples=1)
        predicted_ids = tf.squeeze(predicted_ids, axis=-1)

        # Convert from token ids to characters
        predicted_chars = self.chars_from_ids(predicted_ids)

        # Return the characters and model state.
        return predicted_chars, states


one_step_model = OneStep(model, chars_from_ids, ids_from_chars)


def getResp(chars):
    states = None
    next_char = tf.constant([chars])
    results = [next_char]

    response = list()
    resp_temp = ""

    speaker = None

    for n in range(1000):
        next_char, states = one_step_model.generate_one_step(next_char, states=states)
        results.append(next_char)

        next_char_decoded = next_char.numpy()[0].decode('utf-8')

        if next_char_decoded in [END_RESPONSE, END_QUERY]:
            if speaker is None:
                speaker = next_char_decoded
            elif speaker != next_char_decoded:
                break

            response.append(resp_temp)
            resp_temp = ""
        elif next_char_decoded in SPECIAL_CHARS:
            break
        else:
            resp_temp += next_char_decoded

    # results = tf.strings.join(results)
    # result = results[0].numpy().decode('utf-8')

    # response = result[len(chars):]

    return response


if __name__ == "__main__":
    # one_step_model = OneStep(model, chars_from_ids, ids_from_chars)
    #
    # start = time.time()
    # states = None
    # next_char = tf.constant(['kif int?$'])
    # result = [next_char]
    #
    # for n in range(1000):
    #     next_char, states = one_step_model.generate_one_step(next_char, states=states)
    #     result.append(next_char)
    #
    # result = tf.strings.join(result)

    start = time.time()
    result = getResp("kif int?$")

    end = time.time()
    print(result, '\n\n' + '_' * 80)
    print('\nRun time:', end - start)
