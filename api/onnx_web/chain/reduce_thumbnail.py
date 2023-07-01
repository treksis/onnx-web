from logging import getLogger

from PIL import Image

from ..params import ImageParams, Size, StageParams
from ..server import ServerContext
from ..worker import WorkerContext

logger = getLogger(__name__)


class ReduceThumbnailStage:
    def run(
        self,
        _job: WorkerContext,
        _server: ServerContext,
        _stage: StageParams,
        _params: ImageParams,
        source: Image.Image,
        *,
        size: Size,
        stage_source: Image.Image,
        **kwargs,
    ) -> Image.Image:
        source = stage_source or source
        image = source.copy()

        image = image.thumbnail((size.width, size.height))

        logger.info(
            "created thumbnail with dimensions: %sx%s", image.width, image.height
        )
        return image
