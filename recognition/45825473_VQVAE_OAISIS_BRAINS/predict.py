from os import sys
from os.path import isfile, join
from tensorflow import keras
import train
import tensorflow as tf
from dataset import get_image_slices
from keras.callbacks import History
from skimage.metrics import structural_similarity
import matplotlib.pyplot as plt
import numpy as np

def predict_model_reconstructions(vqvae_trainer, quantizer, priors, encoded_outputs, test_images, number_of_reconstructions):
  # Print the test image and their reconstruction
  trained_vqvae_model = vqvae_trainer.vqvae
  reconstructions_test = trained_vqvae_model.predict(test_images)
  encoder = vqvae_trainer.vqvae.get_layer("encoder")
  quantizer = vqvae_trainer.vqvae.get_layer("vector_quantizer")

  #Generate samples from image
  pretrained_embeddings = quantizer.embeddings
  priors_ohe = tf.one_hot(priors.astype("int32"), vqvae_trainer.num_embeddings).numpy()
  quantized = tf.matmul(priors_ohe.astype("float32"), pretrained_embeddings, transpose_b=True)
  quantized = tf.reshape(quantized, (-1, *(encoded_outputs.shape[1:])))
  decoder = vqvae_trainer.vqvae.get_layer("decoder")
  generated_samples = decoder.predict(quantized)

  for i in range(3):
      plt.subplot(1, 2, 1)
      plt.imshow(test_images[i, :, :, 0])
      plt.title("Original_image")
      plt.axis("off")

      plt.subplot(1, 2, 2)
      plt.imshow(reconstructions_test[i, :, :, 0])
      plt.title("Reconstructed_image")
      plt.axis("off")
      plt.show()

      plt.subplot(1, 2, 1)
      plt.imshow(priors[i,:,:])
      plt.title("Code_image")
      plt.axis("off")

      plt.subplot(1, 2, 2)
      plt.imshow(generated_samples[i, :, :, 0])
      plt.title("Generated Sample_image")
      plt.axis("off")
      plt.show()
  return generated_samples, reconstructions_test

def determine_SSIM(test_images_np, trained_vqvae_model,  generated_samples, reconstructions_test):
    # Compute the Structural Similarity Index (SSIM) between the two images for all test images
    recon_similarity = tf.image.ssim(test_images_np, reconstructions_test, max_val=1)
    print("Mean SSIM: {}".format(recon_similarity))

def plot_losses(vqvaeTrainer):
    x = 1

def main():
    train_images, test_images, validate_images = get_image_slices()
    load_default = False
    if (len(sys.argv) == 3 and sys.argv[1] == "-m"):
        try:
            #TODO load specific model and predict/generate images with loaded model
            print("Loading custom VQVAE model to predict/generate images")
            data_variance = np.var(train_images)
            vqvae_trainer = train.VQVAETrainer(data_variance, latent_dim=16, num_embeddings=32) #Reduced num_embeddings to resolve memory errors
            vqvae_trainer.vqvae = keras.models.load_model("VQVAE_Model") #This needs to be changed to sys.argv[2]
            vqvae_trainer.compile(optimizer=keras.optimizers.Adam())
            vqvae_trainer.fit(train_images, epochs=10, batch_size=32)

            encoder = vqvae_trainer.vqvae.get_layer("encoder")
            quantizer = vqvae_trainer.vqvae.get_layer("vector_quantizer")

            pixel_cnn, sampler = train.construct_and_train_pixelCNN(encoder, quantizer, vqvae_trainer, train_images)

            encoded_outputs = encoder.predict(test_images)
            flat_enc_outputs = encoded_outputs.reshape(-1, encoded_outputs.shape[-1])
            codebook_indices = quantizer.get_code_indices(flat_enc_outputs)
            codebook_indices = codebook_indices.numpy().reshape(encoded_outputs.shape[:-1])

            priors = train.generate_probabilities_for_samples(pixel_cnn, sampler)
            generated, reconstructions_test = predict_model_reconstructions(vqvae_trainer, quantizer, priors,  encoded_outputs,test_images, 10)
            determine_SSIM(test_images, vqvae_trainer.vqvae,  generated, reconstructions_test)
            
        except:
            load_default = True

    elif (len(sys.argv == 1) or load_default):
        print("Loading default model to predict/generate image")
        vqvae_trainer, quantizer, priors, encoded_outputs, pixel_cnn, sampler = train.main()
        encoder = vqvae_trainer.vqvae.get_layer("encoder")
        quantizer = vqvae_trainer.vqvae.get_layer("vector_quantizer")
        encoded_outputs = encoder.predict(test_images)
        flat_enc_outputs = encoded_outputs.reshape(-1, encoded_outputs.shape[-1])
        codebook_indices = quantizer.get_code_indices(flat_enc_outputs)
        codebook_indices = codebook_indices.numpy().reshape(encoded_outputs.shape[:-1])
        priors = train.generate_probabilities_for_samples(pixel_cnn, sampler)
        generated, reconstructions_test = predict_model_reconstructions(vqvae_trainer, quantizer, priors, encoded_outputs, test_images, 10)
        determine_SSIM(test_images, vqvae_trainer.vqvae,  generated, reconstructions_test)
    else:
        print("$ python3 predict.py [-m <PathToPreTrainedModel>]")

if __name__ == "__main__":
    main()