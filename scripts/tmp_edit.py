import pathlib

path = pathlib.Path("apps/tenant/src/modules/usuarios/Form.tsx")
text = path.read_text()
text = text.replace(
    "import React, { useEffect, useMemo, useState } from 'react'",
    "import React, { useEffect, useMemo, useRef, useState } from 'react'",
)
text = text.replace(
    "const { success, error } = useToast()",
    "const toast = useToast()\n  const success = toast.success\n  const errorRef = useRef(toast.error)",
)
text = text.replace("  }, [error])\n\n", "  }, [error])\n\n")
path.write_text(text)
