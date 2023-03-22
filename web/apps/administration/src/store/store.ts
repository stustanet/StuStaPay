import { authApi } from "@api/authApi";
import { combineReducers, configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/dist/query";
import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux";
import {
  productApi,
  userApi,
  taxRateApi,
  tillApi,
  tillLayoutApi,
  tillProfileApi,
  configApi,
  orderApi,
  accountApi,
} from "@api";
import { authSlice } from "./authSlice";
import { uiSlice } from "./uiSlice";
import { persistStore, persistReducer, FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER } from "redux-persist";
import storage from "redux-persist/lib/storage";

const authPersistConfig = {
  key: "auth",
  version: 1,
  storage,
};

const uiPersistConfig = {
  key: "ui",
  version: 1,
  storage,
};

export const store = configureStore({
  reducer: combineReducers({
    [productApi.reducerPath]: productApi.reducer,
    [tillApi.reducerPath]: tillApi.reducer,
    [tillLayoutApi.reducerPath]: tillLayoutApi.reducer,
    [tillProfileApi.reducerPath]: tillProfileApi.reducer,
    [taxRateApi.reducerPath]: taxRateApi.reducer,
    [userApi.reducerPath]: userApi.reducer,
    [authApi.reducerPath]: authApi.reducer,
    [configApi.reducerPath]: configApi.reducer,
    [orderApi.reducerPath]: orderApi.reducer,
    [accountApi.reducerPath]: accountApi.reducer,
    [authSlice.name]: persistReducer(authPersistConfig, authSlice.reducer),
    [uiSlice.name]: persistReducer(uiPersistConfig, uiSlice.reducer),
  }),
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({ serializableCheck: { ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER] } })
      .concat(productApi.middleware)
      .concat(tillApi.middleware)
      .concat(tillLayoutApi.middleware)
      .concat(tillProfileApi.middleware)
      .concat(taxRateApi.middleware)
      .concat(userApi.middleware)
      .concat(configApi.middleware)
      .concat(orderApi.middleware)
      .concat(accountApi.middleware)
      .concat(authApi.middleware),
});

export const persistor = persistStore(store);

setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
