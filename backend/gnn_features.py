import torch
from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn


def build_chess_edges():
    edges = set()
    directions = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]
    knight_offsets = [
        (-2, -1),
        (-2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
        (2, -1),
        (2, 1),
    ]

    for row in range(8):
        for col in range(8):
            source = row * 8 + col

            for dr, dc in directions:
                next_row = row + dr
                next_col = col + dc
                while 0 <= next_row < 8 and 0 <= next_col < 8:
                    target = next_row * 8 + next_col
                    edges.add((source, target))
                    next_row += dr
                    next_col += dc

            for dr, dc in knight_offsets:
                next_row = row + dr
                next_col = col + dc
                if 0 <= next_row < 8 and 0 <= next_col < 8:
                    target = next_row * 8 + next_col
                    edges.add((source, target))

    src, dst = zip(*sorted(edges))
    return torch.tensor(src, dtype=torch.long), torch.tensor(dst, dtype=torch.long)


class GraphConvLayer(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.self_linear = nn.Linear(hidden_dim, hidden_dim)
        self.neighbor_linear = nn.Linear(hidden_dim, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.activation = nn.ReLU()

    def forward(self, node_features, src, dst, degree):
        neighbor_features = node_features.new_zeros(node_features.shape)
        messages = node_features.index_select(1, src)
        neighbor_features.index_add_(1, dst, messages)
        neighbor_features = neighbor_features / degree.view(1, -1, 1).clamp_min(1.0)

        updated = self.self_linear(node_features) + self.neighbor_linear(neighbor_features)
        return self.activation(self.norm(updated))


class ChessGraphFeaturesExtractor(BaseFeaturesExtractor):
    def __init__(
        self,
        observation_space: spaces.Box,
        features_dim=256,
        hidden_dim=128,
        num_layers=3,
    ):
        super().__init__(observation_space, features_dim)

        if observation_space.shape != (8, 8, 13):
            raise ValueError(f"Expected observation shape (8, 8, 13), got {observation_space.shape}")

        src, dst = build_chess_edges()
        degree = torch.bincount(dst, minlength=64).float()

        self.register_buffer("src", src)
        self.register_buffer("dst", dst)
        self.register_buffer("degree", degree)

        self.input_projection = nn.Linear(13, hidden_dim)
        self.square_embedding = nn.Parameter(torch.zeros(64, hidden_dim))
        self.layers = nn.ModuleList(GraphConvLayer(hidden_dim) for _ in range(num_layers))
        self.output_projection = nn.Sequential(
            nn.Linear(hidden_dim * 2, features_dim),
            nn.ReLU(),
            nn.LayerNorm(features_dim),
        )

        nn.init.normal_(self.square_embedding, mean=0.0, std=0.02)

    def forward(self, observations):
        batch_size = observations.shape[0]
        nodes = observations.float().view(batch_size, 64, 13)
        hidden = self.input_projection(nodes) + self.square_embedding.unsqueeze(0)

        for layer in self.layers:
            hidden = layer(hidden, self.src, self.dst, self.degree)

        mean_pool = hidden.mean(dim=1)
        max_pool = hidden.max(dim=1).values
        return self.output_projection(torch.cat([mean_pool, max_pool], dim=1))
