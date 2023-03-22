import * as React from "react";
import {
  selectTillLayoutById,
  useDeleteTillProfileMutation,
  useGetTillLayoutsQuery,
  useGetTillProfilesQuery,
  selectTillProfileAll,
} from "@api";
import { Paper, Typography, ListItem, ListItemText } from "@mui/material";
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { DataGrid, GridActionsCellItem, GridColumns } from "@mui/x-data-grid";
import { ConfirmDialog, ConfirmDialogCloseHandler, ButtonLink } from "@components";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { TillProfile } from "@models";
import { Loading } from "@components/Loading";

export const TillProfileList: React.FC = () => {
  const { t } = useTranslation(["tills", "common"]);
  const navigate = useNavigate();

  const { profiles, isLoading: isTillsLoading } = useGetTillProfilesQuery(undefined, {
    selectFromResult: ({ data, ...rest }) => ({
      ...rest,
      profiles: data ? selectTillProfileAll(data) : undefined,
    }),
  });
  const { data: layouts, isLoading: isLayoutsLoading } = useGetTillLayoutsQuery();
  const [deleteTill] = useDeleteTillProfileMutation();

  const [profileToDelete, setProfileToDelete] = React.useState<number | null>(null);
  if (isTillsLoading || isLayoutsLoading) {
    return <Loading />;
  }

  const renderLayout = (id: number) => {
    if (!layouts) {
      return "";
    }

    const layout = selectTillLayoutById(layouts, id);
    if (!layout) {
      return "";
    }

    return <RouterLink to={`/till-layouts/${layout.id}`}>{layout.name}</RouterLink>;
  };

  const openConfirmDeleteDialog = (tillId: number) => {
    setProfileToDelete(tillId);
  };

  const handleConfirmDeleteProfile: ConfirmDialogCloseHandler = (reason) => {
    if (reason === "confirm" && profileToDelete !== null) {
      deleteTill(profileToDelete)
        .unwrap()
        .catch(() => undefined);
    }
    setProfileToDelete(null);
  };

  const columns: GridColumns<TillProfile> = [
    {
      field: "name",
      headerName: t("profile.name") as string,
      flex: 1,
      renderCell: (params) => <RouterLink to={`/till-profiles/${params.row.id}`}>{params.row.name}</RouterLink>,
    },
    {
      field: "description",
      headerName: t("profile.description") as string,
      flex: 2,
    },
    {
      field: "layout",
      headerName: t("profile.layout") as string,
      flex: 0.5,
      renderCell: (params) => renderLayout(params.row.layout_id),
    },
    {
      field: "actions",
      type: "actions",
      headerName: t("actions", { ns: "common" }) as string,
      width: 150,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<EditIcon />}
          color="primary"
          label={t("edit", { ns: "common" })}
          onClick={() => navigate(`/till-profiles/${params.row.id}/edit`)}
        />,
        <GridActionsCellItem
          icon={<DeleteIcon />}
          color="error"
          label={t("delete", { ns: "common" })}
          onClick={() => openConfirmDeleteDialog(params.row.id)}
        />,
      ],
    },
  ];

  return (
    <>
      <Paper>
        <ListItem
          secondaryAction={
            <ButtonLink to="/till-profiles/new" endIcon={<AddIcon />} variant="contained" color="primary">
              {t("add", { ns: "common" })}
            </ButtonLink>
          }
        >
          <ListItemText primary={t("profile.profiles")} />
        </ListItem>
        <Typography variant="body1">{}</Typography>
      </Paper>
      <DataGrid
        autoHeight
        rows={profiles ?? []}
        columns={columns}
        disableSelectionOnClick
        sx={{ mt: 2, p: 1, boxShadow: (theme) => theme.shadows[1] }}
      />
      <ConfirmDialog
        title={t("profile.delete")}
        body={t("profile.deleteDescription")}
        show={profileToDelete !== null}
        onClose={handleConfirmDeleteProfile}
      />
    </>
  );
};
