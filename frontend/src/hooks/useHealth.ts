import { useQuery } from "@tanstack/react-query";
import { health } from "@/api/endpoints";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
  });
}
