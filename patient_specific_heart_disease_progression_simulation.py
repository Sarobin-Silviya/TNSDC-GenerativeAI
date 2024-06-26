import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# Define the Sampling layer
class Sampling(layers.Layer):
    def call(self, inputs):
        z_mean, z_log_var = inputs
        batch = tf.shape(z_mean)[0]
        dim = tf.shape(z_mean)[1]
        epsilon = tf.random.normal(shape=(batch, dim))
        return z_mean + tf.exp(0.5 * z_log_var) * epsilon

# Import the dataset
data = pd.read_csv('heart.csv')

# Preprocess the data
X_train = data.drop(columns=['target']).values

# Normalize the data
X_train = (X_train - X_train.mean(axis=0)) / X_train.std(axis=0)

# Define the VAE model architecture
latent_dim = 2

encoder_inputs = keras.Input(shape=(X_train.shape[1],))
x = layers.Dense(128, activation='relu')(encoder_inputs)
z_mean = layers.Dense(latent_dim, name="z_mean")(x)
z_log_var = layers.Dense(latent_dim, name="z_log_var")(x)
z = Sampling()([z_mean, z_log_var])
encoder = keras.Model(encoder_inputs, [z_mean, z_log_var, z], name="encoder")

latent_inputs = keras.Input(shape=(latent_dim,))
x = layers.Dense(128, activation='relu')(latent_inputs)
decoder_outputs = layers.Dense(X_train.shape[1], activation='sigmoid')(x)
decoder = keras.Model(latent_inputs, decoder_outputs, name="decoder")

# Define the VAE class
class VAE(keras.Model):
    def __init__(self, encoder, decoder, **kwargs):
        super(VAE, self).__init__(**kwargs)
        self.encoder = encoder
        self.decoder = decoder

    def train_step(self, data):
        if isinstance(data, tuple):
            data = data[0]
        with tf.GradientTape() as tape:
            z_mean, z_log_var, z = self.encoder(data)
            reconstruction = self.decoder(z)
            reconstruction_loss = tf.reduce_mean(
                keras.losses.binary_crossentropy(data, reconstruction)
            )
            reconstruction_loss *= X_train.shape[1]
            kl_loss = 1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var)
            kl_loss = tf.reduce_mean(kl_loss)
            kl_loss *= -0.5
            total_loss = reconstruction_loss + kl_loss
        grads = tape.gradient(total_loss, self.trainable_weights)
        self.optimizer.apply_gradients(zip(grads, self.trainable_weights))
        return {
            "loss": total_loss,
            "reconstruction_loss": reconstruction_loss,
            "kl_loss": kl_loss,
        }

    def call(self, inputs):
        z_mean, z_log_var, z = self.encoder(inputs)
        return self.decoder(z)

# Instantiate VAE
vae = VAE(encoder, decoder)
vae.compile(optimizer=keras.optimizers.Adam())

# Train the VAE model
vae.fit(X_train, epochs=100, batch_size=32, shuffle=True)

# Generate synthetic patient data
synthetic_data = vae.predict(X_train)

# Check for NaN values in synthetic data
if np.isnan(synthetic_data).any():
    print("Synthetic data contains NaN values. Please check your VAE implementation.")
else:
    print("Synthetic data does not contain NaN values.")

import matplotlib.pyplot as plt

# Plot original and reconstructed data
n = 10  # Number of samples to visualize

original_data = X_train[:n]
reconstructed_data = vae.predict(original_data)

fig, axs = plt.subplots(n, 2, figsize=(10, 15))
for i in range(n):
    axs[i, 0].plot(original_data[i], label='Original')
    axs[i, 1].plot(reconstructed_data[i], label='Reconstructed')
    axs[i, 0].set_title('Original Data')
    axs[i, 1].set_title('Reconstructed Data')
    axs[i, 0].legend()
    axs[i, 1].legend()
plt.tight_layout()
plt.show()
