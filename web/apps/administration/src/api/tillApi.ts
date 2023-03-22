import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { Till, NewTill, UpdateTill } from "@models/till";
import { baseUrl, prepareAuthHeaders } from "./common";
import { createEntityAdapter, EntityState } from "@reduxjs/toolkit";
import { convertEntityAdaptorSelectors } from "./utils";

const tillAdapter = createEntityAdapter<Till>({
  sortComparer: (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()),
});

export const tillApi = createApi({
  reducerPath: "tillApi",
  baseQuery: fetchBaseQuery({ baseUrl: baseUrl, prepareHeaders: prepareAuthHeaders }),
  tagTypes: ["tills"],
  endpoints: (builder) => ({
    getTillById: builder.query<EntityState<Till>, number>({
      query: (id) => `/tills/${id}/`,
      transformResponse: (response: Till) => {
        return tillAdapter.addOne(tillAdapter.getInitialState(), response);
      },
      providesTags: (result, error, arg) => ["tills", { type: "tills" as const, id: arg }],
    }),
    getTills: builder.query<EntityState<Till>, void>({
      query: () => "/tills/",
      transformResponse: (response: Till[]) => {
        return tillAdapter.addMany(tillAdapter.getInitialState(), response);
      },
      providesTags: (result, error, arg) =>
        result ? [...result.ids.map((id) => ({ type: "tills" as const, id })), "tills"] : ["tills"],
    }),
    createTill: builder.mutation<Till, NewTill>({
      query: (till) => ({ url: "/tills/", method: "POST", body: till }),
      invalidatesTags: ["tills"],
    }),
    updateTill: builder.mutation<Till, UpdateTill>({
      query: ({ id, ...till }) => ({ url: `/tills/${id}/`, method: "POST", body: till }),
      invalidatesTags: ["tills"],
    }),
    logoutTill: builder.mutation<void, number>({
      query: (id) => ({ url: `/tills/${id}/logout/`, method: "POST" }),
      invalidatesTags: (result, error, arg) => [{ type: "tills", id: arg }],
    }),
    deleteTill: builder.mutation<void, number>({
      query: (id) => ({ url: `/tills/${id}/`, method: "DELETE" }),
      invalidatesTags: ["tills"],
    }),
  }),
});

export const { selectTillAll, selectTillById, selectTillEntities, selectTillIds, selectTillTotal } =
  convertEntityAdaptorSelectors("Till", tillAdapter.getSelectors());

export const {
  useCreateTillMutation,
  useDeleteTillMutation,
  useGetTillByIdQuery,
  useGetTillsQuery,
  useUpdateTillMutation,
  useLogoutTillMutation,
} = tillApi;
