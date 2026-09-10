from __future__ import annotations

import uvicorn

from desktop_operator.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "desktop_operator.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
