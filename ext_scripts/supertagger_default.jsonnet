local gpu = std.parseInt(std.extVar('gpu'));
local char_embedding_dim = 50;
local char_embedded_dim = 100;
local arc_representation_dim = 100;
local tag_representation_dim = 100;
local hidden_dim = 200;
local num_layers = 2;
local train_data = std.extVar('train_data');
local test_data = std.extVar('test_data');
local vocab = std.extVar('vocab');

local JaWiki = {
  token_indexers: {
    tokens: {
      type: 'single_id',
      lowercase_tokens: false,
    },
  },
  text_field_embedder: {
    token_embedders: {
      tokens: {
        type: 'embedding',
        pretrained_file: '/root/vector-wikija/entity_vector/entity_vector.model.txt',
        embedding_dim: 200,
        sparse: true,
      },
    },
  },
  encoder_input_dim: self.text_field_embedder.token_embedders.tokens.embedding_dim,
};

local TokenEmbedding =
    JaWiki {
      token_indexers+: {
        token_characters: {
          type: 'characters',
          character_tokenizer: { end_tokens: ['@@PADDING@@', '@@PADDING@@', '@@PADDING@@', '@@PADDING@@'] },
        },
      },
      text_field_embedder+: {
        token_embedders+: {
          token_characters: {
            type: 'character_encoding',
            embedding: {
              embedding_dim: char_embedding_dim,
              sparse: true,
              trainable: true,
            },
            encoder: {
              type: 'cnn',
              embedding_dim: char_embedding_dim,
              num_filters: char_embedded_dim,
              ngram_filter_sizes: [
                5,
              ],
            },
          },
        },
      },
      encoder_input_dim: super.encoder_input_dim + char_embedded_dim,
    };


local Encoder =
    {
      type: 'lstm',
      input_size: TokenEmbedding.encoder_input_dim,
      hidden_size: hidden_dim,
      num_layers: num_layers,
      dropout: 0.32,
      bidirectional: true,
    };


// main config
{
  vocabulary: {
    directory_path: vocab,
  },
  dataset_reader: {
    type: 'ja_supertagging_dataset',
    lazy: true,
    token_indexers: TokenEmbedding.token_indexers,
  },
  validation_dataset_reader: {
    type: 'ja_supertagging_dataset',
    lazy: true,
    token_indexers: TokenEmbedding.token_indexers,
  },
  train_data_path: train_data,
  validation_data_path: test_data,
  model: {
    type: 'supertagger',
    text_field_embedder: TokenEmbedding.text_field_embedder,
    encoder: Encoder,
    tag_representation_dim: tag_representation_dim,
    arc_representation_dim: arc_representation_dim,
    dropout: 0.32,
    input_dropout: 0.5
  },
  iterator: {
    type: 'bucket',
    cache_instances: false,
    batch_size: 128,
    sorting_keys: [
      [
        'words',
        'num_tokens',
      ],
    ],
  },
  trainer: {
    optimizer: {
      type: 'dense_sparse_adam',
      betas: [
        0.9,
        0.9,
      ],
    },
    learning_rate_scheduler: {
      type: 'reduce_on_plateau',
      mode: 'max',
      factor: 0.5,
      patience: 5,
    },
    validation_metric: '+harmonic_mean',
    grad_norm: 5,
    num_epochs: 100,
    patience: 20,
    cuda_device: gpu,
  },
}