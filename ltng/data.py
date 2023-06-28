from torch.utils.data import DataLoader, Dataset
from lightning.pytorch import LightningDataModule
import pathlib
import numpy as np
from tqdm import tqdm
import soundfile as sf

from datasets.mir1k import MIR1KDataset
from datasets.mpop600 import MPop600Dataset


class LJSpeechDataset(MPop600Dataset):
    test_file_postfix = set(f"LJ001-{i:04d}.wav" for i in range(1, 21))
    valid_file_postfix = set(f"LJ001-{i:04d}.wav" for i in range(21, 101))

    def __init__(
        self,
        wav_dir: str,
        split: str = "train",
        duration: float = 2.0,
        overlap: float = 1.0,
    ):
        wav_dir = pathlib.Path(wav_dir)
        test_files = []
        valid_files = []
        train_files = []
        for f in wav_dir.glob("*.wav"):
            postfix = f.name
            if postfix in self.test_file_postfix:
                test_files.append(f)
            elif postfix in self.valid_file_postfix:
                valid_files.append(f)
            else:
                train_files.append(f)

        if split == "train":
            self.files = train_files
        elif split == "valid":
            self.files = valid_files
        elif split == "test":
            self.files = test_files
        else:
            raise ValueError(f"Unknown split: {split}")

        self.sample_rate = None

        file_lengths = []
        self.samples = []
        self.f0s = []

        print("Gathering files ...")
        for filename in tqdm(self.files):
            x, sr = sf.read(filename)
            if self.sample_rate is None:
                self.sample_rate = sr
                self.segment_num_frames = int(duration * self.sample_rate)
                self.hop_num_frames = int((duration - overlap) * self.sample_rate)
            else:
                assert sr == self.sample_rate
            f0 = np.loadtxt(filename.with_suffix(".pv"))
            # interpolate f0 to frame level
            f0 = np.interp(
                np.arange(0, len(x)),
                np.arange(0, len(f0)) * self.sample_rate * 0.005,
                f0,
            )
            f0[f0 < 80] = 0

            self.f0s.append(f0)
            self.samples.append(x)
            file_lengths.append(
                max(0, x.shape[0] - self.segment_num_frames) // self.hop_num_frames + 1
            )

        self.file_lengths = np.array(file_lengths)
        self.boundaries = np.cumsum(np.array([0] + file_lengths))


class MIR1K(LightningDataModule):
    def __init__(
        self,
        batch_size: int,
        data_dir: str,
        segment: int,
        overlap: int = 0,
        upsample_f0: bool = False,
        in_hertz: bool = True,
    ):
        super().__init__()
        self.save_hyperparameters()

    def setup(self, stage=None):
        if stage == "fit":
            self.train_dataset = MIR1KDataset(
                data_dir=self.hparams.data_dir,
                segment=self.hparams.segment,
                overlap=self.hparams.overlap,
                upsample_f0=self.hparams.upsample_f0,
                in_hertz=self.hparams.in_hertz,
            )

    def train_dataloader(self):
        return DataLoader(
            self.train_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=True,
            drop_last=True,
        )


class MPop600(LightningDataModule):
    def __init__(
        self, batch_size: int, wav_dir: str, duration: float = 2, overlap: float = 0.5
    ):
        super().__init__()
        self.save_hyperparameters()

    def setup(self, stage=None):
        if stage == "fit":
            self.train_dataset = MPop600Dataset(
                wav_dir=self.hparams.wav_dir,
                split="train",
                duration=self.hparams.duration,
                overlap=self.hparams.overlap,
            )

        if stage == "validate" or stage == "fit":
            self.valid_dataset = MPop600Dataset(
                wav_dir=self.hparams.wav_dir,
                split="valid",
                duration=self.hparams.duration,
                overlap=self.hparams.overlap,
            )

        if stage == "test":
            self.test_dataset = MPop600Dataset(
                wav_dir=self.hparams.wav_dir,
                split="test",
                duration=self.hparams.duration,
                overlap=self.hparams.overlap,
            )

    def train_dataloader(self):
        return DataLoader(
            self.train_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=True,
            drop_last=True,
        )

    def val_dataloader(self):
        return DataLoader(
            self.valid_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=False,
            drop_last=False,
        )

    def test_dataloader(self):
        return DataLoader(
            self.test_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=False,
            drop_last=False,
        )


class LJSpeech(LightningDataModule):
    def __init__(
        self,
        batch_size: int,
        wav_dir: str,
        duration: float = 2,
        overlap: float = 0.5,
    ):
        super().__init__()
        self.save_hyperparameters()

    def setup(self, stage=None):
        if stage == "fit":
            self.train_dataset = LJSpeechDataset(
                wav_dir=self.hparams.wav_dir,
                split="train",
                duration=self.hparams.duration,
                overlap=self.hparams.overlap,
            )

        if stage == "validate" or stage == "fit":
            self.valid_dataset = LJSpeechDataset(
                wav_dir=self.hparams.wav_dir,
                split="valid",
                duration=self.hparams.duration,
                overlap=self.hparams.overlap,
            )

        if stage == "test":
            self.test_dataset = LJSpeechDataset(
                wav_dir=self.hparams.wav_dir,
                split="test",
                duration=self.hparams.duration,
                overlap=self.hparams.overlap,
            )

    def train_dataloader(self):
        return DataLoader(
            self.train_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=True,
            drop_last=True,
        )

    def val_dataloader(self):
        return DataLoader(
            self.valid_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=False,
            drop_last=False,
        )

    def test_dataloader(self):
        return DataLoader(
            self.test_dataset,
            batch_size=self.hparams.batch_size,
            num_workers=4,
            shuffle=False,
            drop_last=False,
        )
