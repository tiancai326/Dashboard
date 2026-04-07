# -*- coding: utf-8 -*-
"""
Agricultural Smart Orchard Soil Environment Prediction Model - Encoder-Decoder LSTM
Based on past 72 hours historical data + future 24 hours weather forecast, predict future 24 hours soil temperature, humidity and EC value
"""

import os
import sys
import io

# Set stdout to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pickle
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Auto detect CUDA device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")


class SoilDataset(Dataset):
    """
    Soil environment data dataset class
    Generate sliding window samples: (past 72 hours, future 24 hours forecast, future 24 hours true values)
    """
    def __init__(self, data, encoder_len=72, decoder_len=24, step=1):
        """
        Args:
            data: Normalized complete data
            encoder_len: Encoder input sequence length (past 72 hours)
            decoder_len: Decoder input sequence length (future 24 hours)
            step: Sliding window step
        """
        self.data = data
        self.encoder_len = encoder_len
        self.decoder_len = decoder_len
        self.step = step
        self.total_len = encoder_len + decoder_len
        
        # Calculate number of samples
        self.samples = (len(data) - self.total_len) // step + 1
        
    def __len__(self):
        return self.samples
    
    def __getitem__(self, idx):
        """
        Return a sample
        x1: [encoder_len, 5] - Past 72 hours: air_temp, air_humidity, soil_temp, soil_humidity, ec
        x2: [decoder_len, 2] - Future 24 hours forecast: forecast_temp, forecast_humidity
        y:  [decoder_len, 3] - Future 24 hours true values: soil_temp, soil_humidity, ec
        """
        start_idx = idx * self.step
        end_idx = start_idx + self.total_len
        
        # Get window data
        window = self.data[start_idx:end_idx]
        
        # Encoder input: past 72 hours [72, 5]
        x1 = window[:self.encoder_len, :5]
        
        # Decoder input: future 24 hours weather forecast [24, 2]
        # Use real air_temp, air_humidity from historical data as "perfect weather forecast"
        x2 = window[self.encoder_len:, :2]
        
        # Target output: future 24 hours soil parameters [24, 3]
        y = window[self.encoder_len:, [2, 3, 4]]  # soil_temp, soil_humidity, ec
        
        return torch.FloatTensor(x1), torch.FloatTensor(x2), torch.FloatTensor(y)


class EncoderDecoderLSTM(nn.Module):
    """
    Encoder-Decoder LSTM Model
    For time series prediction
    """
    def __init__(self, encoder_input_dim=5, decoder_input_dim=2, 
                 hidden_dim=128, num_layers=2, output_dim=3, dropout=0.2):
        """
        Args:
            encoder_input_dim: Encoder input dimension (5 features)
            decoder_input_dim: Decoder input dimension (2 forecast features)
            hidden_dim: LSTM hidden layer dimension
            num_layers: Number of LSTM layers
            output_dim: Output dimension (3 target variables)
            dropout: Dropout probability
        """
        super(EncoderDecoderLSTM, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.encoder_input_dim = encoder_input_dim
        self.decoder_input_dim = decoder_input_dim
        
        # Encoder LSTM: process past 72 hours data
        self.encoder_lstm = nn.LSTM(
            input_size=encoder_input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Decoder LSTM: process future 24 hours forecast data
        self.decoder_lstm = nn.LSTM(
            input_size=decoder_input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Fully connected layer: map LSTM output to target dimension
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )
        
    def forward(self, x1, x2):
        """
        Forward propagation
        Args:
            x1: [batch, 72, 5] - Encoder input
            x2: [batch, 24, 2] - Decoder input
        Returns:
            output: [batch, 24, 3] - Prediction result
        """
        batch_size = x1.size(0)
        
        # Encoder: process historical data
        # encoder_output: [batch, 72, hidden_dim]
        # hidden, cell: [num_layers, batch, hidden_dim]
        encoder_output, (hidden, cell) = self.encoder_lstm(x1)
        
        # Decoder: initialize with encoder's hidden state
        # decoder_output: [batch, 24, hidden_dim]
        decoder_output, _ = self.decoder_lstm(x2, (hidden, cell))
        
        # Fully connected layer maps to output dimension
        # output: [batch, 24, 3]
        output = self.fc(decoder_output)
        
        return output


def load_and_preprocess_data(file_path):
    """
    Load and preprocess data
    Args:
        file_path: CSV file path
    Returns:
        df: Preprocessed DataFrame
    """
    print("=" * 60)
    print("1. Loading data")
    print("=" * 60)
    
    # Read CSV file
    df = pd.read_csv(file_path)
    print(f"Raw data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Feature selection: only use specified 5 columns
    # Map column names with units to simple names
    column_mapping = {
        'air_temp(℃)': 'air_temp',
        'air_humidity(%)': 'air_humidity',
        'soil_temp(℃)': 'soil_temp',
        'soil_humidity(%)': 'soil_humidity',
        'ec(μS/cm)': 'ec'
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    feature_cols = ['air_temp', 'air_humidity', 'soil_temp', 'soil_humidity', 'ec']
    df_features = df[feature_cols].copy()
    
    print(f"\nFeature columns: {feature_cols}")
    print(f"Feature data statistics:\n{df_features.describe()}")
    
    # Missing value linear interpolation
    print("\n2. Processing missing values...")
    missing_before = df_features.isnull().sum().sum()
    df_features = df_features.interpolate(method='linear')
    # Fill head and tail if missing
    df_features = df_features.fillna(method='bfill').fillna(method='ffill')
    missing_after = df_features.isnull().sum().sum()
    print(f"Missing values: {missing_before} -> {missing_after}")
    
    # Outlier processing
    print("\n3. Processing outliers...")
    
    # Temperature out of [-10, 50] replaced with mean of before and after
    for col in ['air_temp', 'soil_temp']:
        mask = (df_features[col] < -10) | (df_features[col] > 50)
        if mask.sum() > 0:
            print(f"  {col}: Found {int(mask.sum())} outliers")
            df_features.loc[mask, col] = np.nan
            df_features[col] = df_features[col].interpolate(method='linear')
    
    # Humidity out of [0, 100] replaced with mean of before and after
    for col in ['air_humidity', 'soil_humidity']:
        mask = (df_features[col] < 0) | (df_features[col] > 100)
        if mask.sum() > 0:
            print(f"  {col}: Found {int(mask.sum())} outliers")
            df_features.loc[mask, col] = np.nan
            df_features[col] = df_features[col].interpolate(method='linear')
    
    # EC value should be positive
    mask = df_features['ec'] < 0
    if mask.sum() > 0:
        print(f"  ec: Found {int(mask.sum())} outliers")
        df_features.loc[mask, 'ec'] = np.nan
        df_features['ec'] = df_features['ec'].interpolate(method='linear')
    
    print(f"\nProcessed data statistics:\n{df_features.describe()}")
    
    return df_features


def normalize_data(data):
    """
    Data normalization
    Args:
        data: Raw data [n_samples, 5]
    Returns:
        normalized_data: Normalized data
        scalers: Scaler dictionary
    """
    print("\n4. Data normalization...")
    
    # Separate X1 features (5D), X2 features (2D), Y features (3D)
    # X1: air_temp, air_humidity, soil_temp, soil_humidity, ec
    # X2: air_temp, air_humidity (forecast)
    # Y: soil_temp, soil_humidity, ec
    
    # Create scaler for X1
    x1_scaler = MinMaxScaler()
    x1_data = data  # All 5 features
    x1_normalized = x1_scaler.fit_transform(x1_data)
    
    # Create scaler for X2 (air_temp, air_humidity)
    x2_scaler = MinMaxScaler()
    x2_data = data[:, :2]  # First 2 features
    x2_normalized = x2_scaler.fit_transform(x2_data)
    
    # Create scaler for Y (soil_temp, soil_humidity, ec)
    y_scaler = MinMaxScaler()
    y_data = data[:, [2, 3, 4]]  # 3rd, 4th, 5th features
    y_normalized = y_scaler.fit_transform(y_data)
    
    # Save scalers
    with open('x1_scaler.pkl', 'wb') as f:
        pickle.dump(x1_scaler, f)
    with open('x2_scaler.pkl', 'wb') as f:
        pickle.dump(x2_scaler, f)
    with open('y_scaler.pkl', 'wb') as f:
        pickle.dump(y_scaler, f)
    
    print("  Scalers saved: x1_scaler.pkl, x2_scaler.pkl, y_scaler.pkl")
    
    return x1_normalized, x1_scaler, x2_scaler, y_scaler


def split_data(data, train_ratio=0.8):
    """
    Split training and validation sets by time order
    Args:
        data: Complete data
        train_ratio: Training set ratio
    Returns:
        train_data, val_data
    """
    print("\n5. Splitting training and validation sets...")
    
    n_samples = len(data)
    train_size = int(n_samples * train_ratio)
    
    train_data = data[:train_size]
    val_data = data[train_size:]
    
    print(f"  Total samples: {n_samples}")
    print(f"  Training set: {train_size} ({int(train_ratio*100)}%)")
    print(f"  Validation set: {n_samples - train_size} ({int((1-train_ratio)*100)}%)")
    
    return train_data, val_data


def train_model(model, train_loader, val_loader, epochs=100, patience=10, lr=0.001):
    """
    Train model
    Args:
        model: Model instance
        train_loader: Training data loader
        val_loader: Validation data loader
        epochs: Maximum training epochs
        patience: Early stopping patience
        lr: Learning rate
    Returns:
        model: Trained model
        history: Training history
    """
    print("\n" + "=" * 60)
    print("6. Starting training")
    print("=" * 60)
    
    # Loss function and optimizer
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    # Training history
    history = {'train_loss': [], 'val_loss': []}
    
    # Early stopping variables
    best_val_loss = float('inf')
    patience_counter = 0
    best_model_state = None
    
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_losses = []
        
        for x1, x2, y in train_loader:
            x1, x2, y = x1.to(device), x2.to(device), y.to(device)
            
            # Forward propagation
            optimizer.zero_grad()
            output = model(x1, x2)
            loss = criterion(output, y)
            
            # Backward propagation
            loss.backward()
            optimizer.step()
            
            train_losses.append(loss.item())
        
        avg_train_loss = np.mean(train_losses)
        history['train_loss'].append(avg_train_loss)
        
        # Validation phase
        model.eval()
        val_losses = []
        
        with torch.no_grad():
            for x1, x2, y in val_loader:
                x1, x2, y = x1.to(device), x2.to(device), y.to(device)
                output = model(x1, x2)
                loss = criterion(output, y)
                val_losses.append(loss.item())
        
        avg_val_loss = np.mean(val_losses)
        history['val_loss'].append(avg_val_loss)
        
        # Print every 10 epochs
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}] - "
                  f"Train Loss: {avg_train_loss:.6f}, "
                  f"Val Loss: {avg_val_loss:.6f}")
        
        # Early stopping check
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"\nEarly stopping triggered! Best validation loss: {best_val_loss:.6f}")
                break
    
    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        print(f"\nLoaded best model (validation loss: {best_val_loss:.6f})")
    
    return model, history


def plot_loss_curve(history):
    """
    Plot loss curve
    Args:
        history: Training history
    """
    plt.figure(figsize=(10, 6))
    plt.plot(history['train_loss'], label='Train Loss', linewidth=2)
    plt.plot(history['val_loss'], label='Validation Loss', linewidth=2)
    plt.xlabel('Epoch', fontsize=12)
    plt.ylabel('MSE Loss', fontsize=12)
    plt.title('Training and Validation Loss Curve', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('loss_curve.png', dpi=150)
    print("Loss curve saved: loss_curve.png")
    plt.close()


def evaluate_and_visualize(model, val_loader, y_scaler):
    """
    Evaluate model and visualize prediction results
    Args:
        model: Trained model
        val_loader: Validation data loader
        y_scaler: Y scaler
    """
    print("\n" + "=" * 60)
    print("7. Model evaluation")
    print("=" * 60)
    
    model.eval()
    
    # Collect all predictions and true values
    all_preds = []
    all_true = []
    
    with torch.no_grad():
        for x1, x2, y in val_loader:
            x1, x2 = x1.to(device), x2.to(device)
            output = model(x1, x2)
            all_preds.append(output.cpu().numpy())
            all_true.append(y.numpy())
    
    # Concatenate all batches
    all_preds = np.concatenate(all_preds, axis=0)  # [n_samples, 24, 3]
    all_true = np.concatenate(all_true, axis=0)    # [n_samples, 24, 3]
    
    # Inverse normalization
    # Reshape to 2D for inverse transformation
    n_samples, seq_len, n_features = all_preds.shape
    preds_2d = all_preds.reshape(-1, n_features)
    true_2d = all_true.reshape(-1, n_features)
    
    preds_inv = y_scaler.inverse_transform(preds_2d).reshape(n_samples, seq_len, n_features)
    true_inv = y_scaler.inverse_transform(true_2d).reshape(n_samples, seq_len, n_features)
    
    # Calculate evaluation metrics
    target_names = ['Soil Temperature', 'Soil Humidity', 'EC']
    print("\nEvaluation metrics:")
    
    for i, name in enumerate(target_names):
        mae = mean_absolute_error(true_inv[:, :, i].flatten(), preds_inv[:, :, i].flatten())
        rmse = np.sqrt(mean_squared_error(true_inv[:, :, i].flatten(), preds_inv[:, :, i].flatten()))
        print(f"  {name}:")
        print(f"    MAE: {mae:.4f}")
        print(f"    RMSE: {rmse:.4f}")
    
    # Plot prediction comparison for last validation sample
    last_sample_idx = -1
    last_pred = preds_inv[last_sample_idx]  # [24, 3]
    last_true = true_inv[last_sample_idx]   # [24, 3]
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    hours = range(24)
    
    for i, (name, unit) in enumerate(zip(target_names, ['C', '%', 'uS/cm'])):
        axes[i].plot(hours, last_true[:, i], 'b-', label='True', linewidth=2, marker='o')
        axes[i].plot(hours, last_pred[:, i], 'r--', label='Predicted', linewidth=2, marker='x')
        axes[i].set_xlabel('Hour', fontsize=11)
        axes[i].set_ylabel(f'{name} ({unit})', fontsize=11)
        axes[i].set_title(f'{name} Prediction (Last Validation Sample)', fontsize=12)
        axes[i].legend(fontsize=10)
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('predictions.png', dpi=150)
    print("\nPrediction comparison saved: predictions.png")
    plt.close()
    
    return preds_inv, true_inv


def predict(history_data, forecast_data, model_path='best_model.pth'):
    """
    Inference function: for deployment
    Args:
        history_data: Past 72 hours data [72, 5] - air_temp, air_humidity, soil_temp, soil_humidity, ec
        forecast_data: Future 24 hours weather forecast [24, 2] - forecast_temp, forecast_humidity
        model_path: Model weights path
    Returns:
        predictions: Prediction results [24, 3] - soil_temp, soil_humidity, ec
    """
    # Load model
    model = EncoderDecoderLSTM().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # Load scalers
    with open('x1_scaler.pkl', 'rb') as f:
        x1_scaler = pickle.load(f)
    with open('x2_scaler.pkl', 'rb') as f:
        x2_scaler = pickle.load(f)
    with open('y_scaler.pkl', 'rb') as f:
        y_scaler = pickle.load(f)
    
    # Normalize input data
    history_normalized = x1_scaler.transform(history_data)
    forecast_normalized = x2_scaler.transform(forecast_data)
    
    # Convert to tensor
    x1 = torch.FloatTensor(history_normalized).unsqueeze(0).to(device)  # [1, 72, 5]
    x2 = torch.FloatTensor(forecast_normalized).unsqueeze(0).to(device)  # [1, 24, 2]
    
    # Predict
    with torch.no_grad():
        output = model(x1, x2)  # [1, 24, 3]
    
    # Inverse normalization
    output_np = output.cpu().numpy()[0]  # [24, 3]
    predictions = y_scaler.inverse_transform(output_np)
    
    return predictions


def main():
    """Main function"""
    print("=" * 60)
    print("Agricultural Smart Orchard Soil Environment Prediction Model")
    print("Encoder-Decoder LSTM")
    print("=" * 60)
    
    # 1. Load and preprocess data
    data = load_and_preprocess_data('sensor_data.csv')
    
    # 2. Data normalization
    normalized_data, x1_scaler, x2_scaler, y_scaler = normalize_data(data.values)
    
    # 3. Split training and validation sets
    train_data, val_data = split_data(normalized_data, train_ratio=0.8)
    
    # 4. Create dataset and data loaders
    print("\n6. Creating data loaders...")
    train_dataset = SoilDataset(train_data, encoder_len=72, decoder_len=24, step=1)
    val_dataset = SoilDataset(val_data, encoder_len=72, decoder_len=24, step=1)
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
    
    print(f"  Training samples: {len(train_dataset)}")
    print(f"  Validation samples: {len(val_dataset)}")
    
    # Check if we have enough samples
    if len(train_dataset) == 0 or len(val_dataset) == 0:
        print("\nError: Not enough data samples!")
        print(f"  Total data length: {len(normalized_data)}")
        print(f"  Required minimum: 96 (72 + 24)")
        return
    
    # 5. Create model
    print("\n7. Creating model...")
    model = EncoderDecoderLSTM(
        encoder_input_dim=5,
        decoder_input_dim=2,
        hidden_dim=128,
        num_layers=2,
        output_dim=3,
        dropout=0.2
    ).to(device)
    
    print(f"  Total model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # 6. Train model
    if len(train_dataset) > 0 and len(val_dataset) > 0:
        model, history = train_model(
            model, train_loader, val_loader,
            epochs=100, patience=10, lr=0.001
        )
    else:
        print("\nSkipping training due to insufficient data.")
        return
    
    # 7. Save best model
    if len(train_dataset) > 0 and len(val_dataset) > 0:
        torch.save(model.state_dict(), 'best_model.pth')
        print("\nModel saved: best_model.pth")
        
        # 8. Plot loss curve
        plot_loss_curve(history)
        
        # 9. Evaluate and visualize
        evaluate_and_visualize(model, val_loader, y_scaler)
    
    print("\n" + "=" * 60)
    print("Training completed!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - best_model.pth (model weights)")
    print("  - x1_scaler.pkl, x2_scaler.pkl, y_scaler.pkl (scalers)")
    print("  - loss_curve.png (loss curve)")
    print("  - predictions.png (prediction comparison)")
    print("\nInference example:")
    print("  from train import predict")
    print("  predictions = predict(history_data, forecast_data)")


if __name__ == '__main__':
    main()
