"use client";

import { useState, useEffect } from "react";

export function useLiveData<T>(apiPath: string, fallback: T): { data: T; isLive: boolean; loading: boolean } {
  const [data, setData] = useState<T>(fallback);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(apiPath)
      .then((r) => r.json())
      .then((json) => {
        if (json.live !== false && json) {
          setData(json);
          setIsLive(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiPath]);

  return { data, isLive, loading };
}
