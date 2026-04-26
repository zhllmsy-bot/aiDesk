export type TestIdProps = {
  "data-testid"?: string;
};

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function dataTestId(props: object, fallback: string) {
  return (props as TestIdProps)["data-testid"] ?? fallback;
}
