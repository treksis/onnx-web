import { doesExist, Maybe, mustExist } from '@apextoaster/js-utils';
import { FormatColorFill, Gradient } from '@mui/icons-material';
import { Button, Stack } from '@mui/material';
import { throttle } from 'lodash';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ConfigParams, DEFAULT_BRUSH, SAVE_TIME } from '../config.js';
import { NumericField } from './NumericField';

export const FULL_CIRCLE = 2 * Math.PI;
export const PIXEL_SIZE = 4;
export const PIXEL_WEIGHT = 3;

export const COLORS = {
  black: 0,
  white: 255,
};

export const THRESHOLDS = {
  lower: 34,
  upper: 224,
};

export const MASK_STATE = {
  clean: 'clean',
  painting: 'painting',
  dirty: 'dirty',
};

export function floodBelow(n: number): number {
  if (n < THRESHOLDS.upper) {
    return COLORS.black;
  } else {
    return COLORS.white;
  }
}

export function floodAbove(n: number): number {
  if (n > THRESHOLDS.lower) {
    return COLORS.white;
  } else {
    return COLORS.black;
  }
}

export function floodGray(n: number): number {
  return n;
}

export function grayToRGB(n: number): string {
  return `rgb(${n.toFixed(0)},${n.toFixed(0)},${n.toFixed(0)})`;
}

export type FloodFn = (n: number) => number;

export interface Point {
  x: number;
  y: number;
}

export interface MaskCanvasProps {
  config: ConfigParams;

  source?: Maybe<Blob>;

  onSave: (blob: Blob) => void;
}

export function MaskCanvas(props: MaskCanvasProps) {
  const { config, source } = props;

  function floodMask(flood: FloodFn) {
    const canvas = mustExist(canvasRef.current);
    const ctx = mustExist(canvas.getContext('2d'));
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = image.data;

    for (let x = 0; x < canvas.width; ++x) {
      for (let y = 0; y < canvas.height; ++y) {
        const i = (y * canvas.width * PIXEL_SIZE) + (x * PIXEL_SIZE);
        const hue = (pixels[i] + pixels[i + 1] + pixels[i + 2]) / PIXEL_WEIGHT;
        const final = flood(hue);

        pixels[i] = final;
        pixels[i + 1] = final;
        pixels[i + 2] = final;
      }
    }

    ctx.putImageData(image, 0, 0);
    save();
  }

  function saveMask(): void {
    // eslint-disable-next-line no-console
    console.log('starting canvas save');

    if (doesExist(canvasRef.current)) {
      if (state.current === MASK_STATE.clean) {
        // eslint-disable-next-line no-console
        console.log('attempting to save a clean canvas');
        return;
      }

      canvasRef.current.toBlob((blob) => {
        // eslint-disable-next-line no-console
        console.log('finishing canvas save');

        state.current = MASK_STATE.clean;
        props.onSave(mustExist(blob));
      });
    } else {
      // eslint-disable-next-line no-console
      console.log('canvas no longer exists');
    }
  }

  function drawCircle(ctx: CanvasRenderingContext2D, point: Point): void {
    ctx.beginPath();
    ctx.arc(point.x, point.y, brushSize, 0, FULL_CIRCLE);
    ctx.fill();
  }

  function drawSource(file: Blob): void {
    const image = new Image();
    image.onload = () => {
      const canvas = mustExist(canvasRef.current);
      const ctx = mustExist(canvas.getContext('2d'));
      ctx.drawImage(image, 0, 0);
      URL.revokeObjectURL(src);
    };

    const src = URL.createObjectURL(file);
    image.src = src;
  }

  function finishPainting() {
    if (state.current === MASK_STATE.painting) {
      state.current = MASK_STATE.dirty;
      save();
    }
  }

  const save = useMemo(() => throttle(saveMask, SAVE_TIME), []);

  // eslint-disable-next-line no-null/no-null
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // painting state
  const state = useRef(MASK_STATE.clean);
  const [clicks, setClicks] = useState<Array<Point>>([]);
  const [brushColor, setBrushColor] = useState(DEFAULT_BRUSH.color);
  const [brushSize, setBrushSize] = useState(DEFAULT_BRUSH.size);

  useEffect(() => {
    // including clicks.length prevents the initial render from saving a blank canvas
    if (doesExist(canvasRef.current) && state.current === MASK_STATE.painting && clicks.length > 0) {
      const ctx = mustExist(canvasRef.current.getContext('2d'));
      ctx.fillStyle = grayToRGB(brushColor);

      for (const click of clicks) {
        drawCircle(ctx, click);
      }

      clicks.length = 0;
    }
  }, [clicks.length]);

  useEffect(() => {
    // eslint-disable-next-line no-console
    console.log('state hook called', state.current);
    if (state.current === MASK_STATE.dirty) {
      save();
    }
  }, [state.current]);

  useEffect(() => {
    if (doesExist(canvasRef.current) && doesExist(source)) {
      drawSource(source);
    }
  }, [source]);

  return <Stack spacing={2}>
    <canvas
      ref={canvasRef}
      height={config.height.default}
      width={config.width.default}
      style={{
        maxHeight: config.height.default,
        maxWidth: config.width.default,
      }}
      onClick={(event) => {
        const canvas = mustExist(canvasRef.current);
        const bounds = canvas.getBoundingClientRect();
        const ctx = mustExist(canvas.getContext('2d'));
        ctx.fillStyle = grayToRGB(brushColor);

        drawCircle(ctx, {
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        });

        state.current = MASK_STATE.dirty;
        save();
      }}
      onMouseDown={() => {
        state.current = MASK_STATE.painting;
      }}
      onMouseLeave={finishPainting}
      onMouseOut={finishPainting}
      onMouseUp={finishPainting}
      onMouseMove={(event) => {
        if (state.current === MASK_STATE.painting) {
          const canvas = mustExist(canvasRef.current);
          const bounds = canvas.getBoundingClientRect();

          setClicks([...clicks, {
            x: event.clientX - bounds.left,
            y: event.clientY - bounds.top,
          }]);
        }
      }}
    />
    <Stack direction='row' spacing={4}>
      <NumericField
        decimal
        label='Brush Shade'
        min={0}
        max={255}
        step={1}
        value={brushColor}
        onChange={(value) => {
          setBrushColor(value);
        }}
      />
      <NumericField
        decimal
        label='Brush Size'
        min={4}
        max={64}
        step={1}
        value={brushSize}
        onChange={(value) => {
          setBrushSize(value);
        }}
      />
      <Button
        variant='outlined'
        startIcon={<FormatColorFill />}
        onClick={() => floodMask(floodBelow)}>
        Gray to black
      </Button>
      <Button
        variant='outlined'
        startIcon={<Gradient />}
        onClick={() => floodMask(floodGray)}>
        Grayscale
      </Button>
      <Button
        variant='outlined'
        startIcon={<FormatColorFill />}
        onClick={() => floodMask(floodAbove)}>
        Gray to white
      </Button>
    </Stack></Stack>;
}
