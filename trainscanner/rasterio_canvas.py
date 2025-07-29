#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
import cv2
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class RasterioCanvas:
    """
    Rasterioを使用してGeoTIFF形式で画像を処理するキャンバスクラス
    CachedImageの代替として使用
    """
    
    def __init__(self, mode="new", dir=None, tilesize=(512, 512), cachesize=10):
        """
        RasterioCanvasを初期化
        
        Args:
            mode: "new" または "inherit"
            dir: 作業ディレクトリ
            tilesize: タイルサイズ (width, height)
            cachesize: キャッシュサイズ（未使用、互換性のため）
        """
        self.mode = mode
        self.dir = dir or tempfile.mkdtemp()
        self.tilesize = tilesize
        self.cachesize = cachesize
        
        # キャンバスの状態を管理
        self.canvas_width = 0
        self.canvas_height = 0
        self.channels = 3
        self.transform = None
        self.crs = rasterio.crs.CRS.from_epsg(4326)  # WGS84
        
        # オフセット管理（負の座標対応）
        self.offset_x = 0
        self.offset_y = 0
        
        # 一時ファイルのパス
        self.temp_file = None
        
        # フック関数を初期化
        self.hook_function = None
        
        # キャンバスが初期化されているかどうか
        self.canvas_initialized = False
        
        logger.debug(f"RasterioCanvas initialized with dir: {self.dir}")
    
    def initialize_canvas(self, width, height):
        """
        キャンバスを初期化
        
        Args:
            width: キャンバスの幅
            height: キャンバスの高さ
        """
        if self.canvas_initialized:
            return
        
        self.canvas_width = width
        self.canvas_height = height
        
        # 一時ファイルを作成
        self.temp_file = os.path.join(self.dir, "canvas.tiff")
        
        # 空のGeoTIFFファイルを作成
        with rasterio.open(
            self.temp_file,
            'w',
            driver='GTiff',
            height=self.canvas_height,
            width=self.canvas_width,
            count=self.channels,
            dtype=np.uint8,
            crs=self.crs,
            transform=from_origin(0, self.canvas_height, 1, 1)
        ) as dst:
            # 空のデータを書き込み
            empty_data = np.zeros((self.channels, self.canvas_height, self.canvas_width), dtype=np.uint8)
            dst.write(empty_data)
        
        self.canvas_initialized = True
        logger.debug(f"Canvas initialized: {self.canvas_width}x{self.canvas_height}")
    
    def _expand_canvas_if_needed(self, x, y, img_width, img_height):
        """
        必要に応じてキャンバスを拡張
        
        Args:
            x, y: 画像の配置位置
            img_width, img_height: 画像のサイズ
        
        Returns:
            (new_x, new_y): 調整された座標
        """
        new_offset_x = self.offset_x
        new_offset_y = self.offset_y
        new_width = self.canvas_width
        new_height = self.canvas_height
        
        # 負の座標の場合、オフセットを調整
        if x < 0:
            new_offset_x = min(new_offset_x, x)
            new_width = max(new_width, abs(x) + img_width)
        if y < 0:
            new_offset_y = min(new_offset_y, y)
            new_height = max(new_height, abs(y) + img_height)
        
        # キャンバスサイズを拡張する必要がある場合
        if (new_offset_x != self.offset_x or new_offset_y != self.offset_y or 
            new_width != self.canvas_width or new_height != self.canvas_height):
            
            # 新しいキャンバスサイズを計算
            total_width = max(new_width, self.canvas_width + abs(new_offset_x - self.offset_x))
            total_height = max(new_height, self.canvas_height + abs(new_offset_y - self.offset_y))
            
            # 新しい一時ファイルを作成
            new_temp_file = os.path.join(self.dir, "canvas_new.tiff")
            
            with rasterio.open(
                new_temp_file,
                'w',
                driver='GTiff',
                height=total_height,
                width=total_width,
                count=self.channels,
                dtype=np.uint8,
                crs=self.crs,
                transform=from_origin(new_offset_x, new_offset_y + total_height, 1, 1)
            ) as dst:
                # 空のデータを書き込み
                empty_data = np.zeros((self.channels, total_height, total_width), dtype=np.uint8)
                dst.write(empty_data)
            
            # 既存のデータを新しいキャンバスにコピー
            if self.canvas_initialized:
                with rasterio.open(self.temp_file, 'r') as src:
                    old_data = src.read()
                
                with rasterio.open(new_temp_file, 'r+') as dst:
                    # オフセットの差を計算
                    dx = self.offset_x - new_offset_x
                    dy = self.offset_y - new_offset_y
                    
                    # 既存データを新しい位置にコピー
                    if dx >= 0 and dy >= 0:
                        dst.write(old_data, window=((dy, dy + self.canvas_height), (dx, dx + self.canvas_width)))
                
                # 古いファイルを削除
                os.remove(self.temp_file)
            
            # 新しいファイルを現在のファイルとして設定
            self.temp_file = new_temp_file
            self.canvas_width = total_width
            self.canvas_height = total_height
            self.offset_x = new_offset_x
            self.offset_y = new_offset_y
            self.canvas_initialized = True
            
            logger.debug(f"Canvas expanded to {self.canvas_width}x{self.canvas_height} with offset ({self.offset_x}, {self.offset_y})")
        
        # 調整された座標を返す
        adjusted_x = x - self.offset_x
        adjusted_y = y - self.offset_y
        
        return adjusted_x, adjusted_y
    
    def put_image(self, position, image, linear_alpha=None):
        """
        画像をキャンバスの指定位置に配置
        
        Args:
            position: (x, y) 座標
            image: 配置する画像（numpy配列）
            linear_alpha: アルファブレンディング用のマスク
        """
        x, y = position
        
        # 最初の画像の場合、キャンバスを初期化
        if not self.canvas_initialized:
            # 画像サイズに基づいてキャンバスサイズを推定
            # 実際の使用では、Stitcherからcanvasサイズが渡される
            canvas_width = max(x + image.shape[1], 1000)
            canvas_height = max(y + image.shape[0], 1000)
            self.initialize_canvas(canvas_width, canvas_height)
        
        # 画像をRGB形式に変換
        if len(image.shape) == 3 and image.shape[2] == 3:
            # BGRからRGBに変換
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # 画像のサイズを取得
        img_height, img_width = image_rgb.shape[:2]
        
        # 必要に応じてキャンバスを拡張し、座標を調整
        adjusted_x, adjusted_y = self._expand_canvas_if_needed(x, y, img_width, img_height)
        
        # 調整された座標がキャンバス内かチェック
        if (adjusted_x < 0 or adjusted_y < 0 or 
            adjusted_x + img_width > self.canvas_width or 
            adjusted_y + img_height > self.canvas_height):
            logger.warning(f"Image position {position} with size {image_rgb.shape} is outside canvas bounds {self.canvas_width}x{self.canvas_height}")
            return
        
        # GeoTIFFファイルを読み込み
        with rasterio.open(self.temp_file, 'r+') as dst:
            # 既存のデータを読み込み
            existing_data = dst.read()
            
            # アルファブレンディングを適用
            if linear_alpha is not None:
                # アルファマスクを正規化
                alpha = linear_alpha.astype(np.float32) / 255.0
                if len(alpha.shape) == 3:
                    alpha = alpha[:, :, 0:1]  # 単一チャンネルに変換
                
                # 既存の画像領域を取得
                existing_region = existing_data[:, adjusted_y:adjusted_y+img_height, adjusted_x:adjusted_x+img_width]
                
                # アルファブレンディング
                if existing_region.shape[1:] == image_rgb.shape[:2]:
                    # 画像をチャンネル次元で並べ替え
                    image_channels = np.transpose(image_rgb, (2, 0, 1))
                    blended = (1 - alpha) * existing_region + alpha * image_channels
                    blended = blended.astype(np.uint8)
                else:
                    # サイズが異なる場合は単純に置き換え
                    image_channels = np.transpose(image_rgb, (2, 0, 1))
                    blended = image_channels
            else:
                # アルファブレンディングなしで単純に置き換え
                image_channels = np.transpose(image_rgb, (2, 0, 1))
                blended = image_channels
            
            # データを書き込み
            existing_data[:, adjusted_y:adjusted_y+img_height, adjusted_x:adjusted_x+img_width] = blended
            dst.write(existing_data)
        
        logger.debug(f"Image placed at position {position} (adjusted: {adjusted_x}, {adjusted_y}), size: {image.shape}")
        
        # フック関数が設定されている場合は呼び出す
        if hasattr(self, 'hook_function') and self.hook_function is not None:
            self.hook_function(position, image)
    
    def get_image(self):
        """
        完成した画像を取得
        
        Returns:
            numpy配列の画像
        """
        if not self.canvas_initialized:
            return None
        
        # GeoTIFFファイルを読み込み
        with rasterio.open(self.temp_file, 'r') as src:
            # データを読み込み
            data = src.read()
            
            # チャンネル次元を最後に移動
            image = np.transpose(data, (1, 2, 0))
            
            # RGBからBGRに変換してOpenCV形式に戻す
            if len(image.shape) == 3 and image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                return image
    
    def save_geotiff(self, filename):
        """
        画像をGeoTIFF形式で保存
        
        Args:
            filename: 保存するファイル名
        """
        if not self.canvas_initialized:
            logger.warning("No canvas to save")
            return
        
        # 既存のファイルをコピー
        import shutil
        shutil.copy2(self.temp_file, filename)
        logger.info(f"GeoTIFF saved to {filename}")
    
    def done(self):
        """
        処理完了時のクリーンアップ（互換性のため）
        """
        logger.debug("RasterioCanvas done")
    
    def get_region(self, region):
        """
        画像の特定領域を取得（互換性のため）
        
        Args:
            region: 取得する領域 (x, y, width, height) または None（全体）
        
        Returns:
            指定された領域の画像
        """
        if not self.canvas_initialized:
            return None
        
        if region is None:
            return self.get_image()
        
        x, y, width, height = region
        
        # 座標をオフセットで調整
        adjusted_x = x - self.offset_x
        adjusted_y = y - self.offset_y
        
        # 調整された座標がキャンバス内かチェック
        if (adjusted_x < 0 or adjusted_y < 0 or 
            adjusted_x + width > self.canvas_width or 
            adjusted_y + height > self.canvas_height):
            logger.warning(f"Region {region} is outside canvas bounds")
            return None
        
        # GeoTIFFファイルから特定領域を読み込み
        with rasterio.open(self.temp_file, 'r') as src:
            data = src.read(window=((adjusted_y, adjusted_y+height), (adjusted_x, adjusted_x+width)))
            image = np.transpose(data, (1, 2, 0))
            
            # RGBからBGRに変換
            if len(image.shape) == 3 and image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                return image
    
    def set_hook(self, hook_function):
        """
        フック関数を設定（互換性のため）
        
        Args:
            hook_function: 画像が配置された時に呼ばれる関数
        """
        self.hook_function = hook_function
    
    def add_hook(self, hook_function):
        """
        フック関数を追加（互換性のため）
        
        Args:
            hook_function: 画像が配置された時に呼ばれる関数
        """
        self.hook_function = hook_function 