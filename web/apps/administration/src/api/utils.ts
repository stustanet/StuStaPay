import { EntitySelectors, EntityState } from "@reduxjs/toolkit";

const capitalize = <S extends string>(val: S): Capitalize<S> => {
  return (val.charAt(0).toUpperCase() + val.slice(1)) as Capitalize<S>;
};

export type RemovePrefix<S extends string, Prefix extends string> = S extends `${Prefix}${infer T}` ? T : S;

export type ConvertReturn<T, N extends string> = {
  [K in keyof EntitySelectors<T, EntityState<T>> as `select${Capitalize<N>}${RemovePrefix<
    K,
    "select"
  >}`]: EntitySelectors<T, EntityState<T>>[K];
};

export const convertEntityAdaptorSelectors = <T, N extends string>(
  name: N,
  selectors: EntitySelectors<T, EntityState<T>>
): ConvertReturn<T, N> => {
  const c = capitalize(name);
  return {
    [`select${c}All`]: selectors.selectAll,
    [`select${c}ById`]: selectors.selectById,
    [`select${c}Entities`]: selectors.selectEntities,
    [`select${c}Ids`]: selectors.selectIds,
    [`select${c}Total`]: selectors.selectTotal,
  } as ConvertReturn<T, N>;
};
