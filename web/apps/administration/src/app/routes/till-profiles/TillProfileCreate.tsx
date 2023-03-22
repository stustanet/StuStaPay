import * as React from "react";
import { NewTillProfile, NewTillProfileSchema } from "@models";
import { useCreateTillProfileMutation } from "@api";
import { useTranslation } from "react-i18next";
import { TillProfileChange } from "./TillProfileChange";

const initialValues: NewTillProfile = {
  name: "",
  description: "",
  layout_id: undefined as unknown as number, // TODO
};

export const TillProfileCreate: React.FC = () => {
  const { t } = useTranslation(["tills", "common"]);
  const [createLayout] = useCreateTillProfileMutation();

  return (
    <TillProfileChange
      headerTitle={t("profile.create")}
      submitLabel={t("add", { ns: "common" })}
      initialValues={initialValues}
      validationSchema={NewTillProfileSchema}
      onSubmit={createLayout}
    />
  );
};
