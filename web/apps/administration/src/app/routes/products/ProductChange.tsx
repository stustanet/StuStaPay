import { Paper, TextField, Button, LinearProgress, Typography, FormControlLabel, Checkbox } from "@mui/material";
import * as React from "react";
import { Formik, Form, FormikHelpers } from "formik";
import { NewProduct } from "../../../models/product";
import { toFormikValidationSchema } from "@stustapay/utils";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { TaxRateSelect } from "./TaxRateSelect";
import { NumericInput } from "../../../components/NumericInput";
import { MutationActionCreatorResult } from "@reduxjs/toolkit/dist/query/core/buildInitiate";

export interface ProductChangeProps<T extends NewProduct> {
  headerTitle: string;
  submitLabel: string;
  initialValues: T;
  validationSchema: z.ZodSchema<T>;
  onSubmit: (p: T) => MutationActionCreatorResult<any>;
}

export function ProductChange<T extends NewProduct>({
  headerTitle,
  initialValues,
  submitLabel,
  validationSchema,
  onSubmit,
}: ProductChangeProps<T>) {
  const navigate = useNavigate();
  const { t } = useTranslation(["products", "common"]);
  const handleSubmit = (values: T, { setSubmitting }: FormikHelpers<T>) => {
    setSubmitting(true);

    onSubmit(values)
      .unwrap()
      .then(() => {
        setSubmitting(false);
        navigate("/products");
      })
      .catch((err) => {
        setSubmitting(false);
        console.warn("error", err);
      });
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5">{headerTitle}</Typography>
      <Formik
        initialValues={initialValues}
        onSubmit={handleSubmit}
        validationSchema={toFormikValidationSchema(validationSchema)}
      >
        {({ values, handleBlur, handleChange, handleSubmit, isSubmitting, setFieldValue, errors, touched }) => (
          <Form onSubmit={handleSubmit}>
            <TextField
              variant="standard"
              margin="normal"
              fullWidth
              autoFocus
              name="name"
              label={t("productName")}
              error={touched.name && !!errors.name}
              helperText={(touched.name && errors.name) as string}
              onBlur={handleBlur}
              onChange={handleChange}
              value={values.name}
            />

            <FormControlLabel
              label={t("fixedPrice")}
              control={
                <Checkbox
                  checked={values.fixed_price}
                  onChange={(evt) => {
                    const checked = evt.target.checked;
                    setFieldValue("fixed_price", checked);
                    if (!checked) {
                      setFieldValue("price", null);
                    }
                  }}
                />
              }
            />

            {values.fixed_price && (
              <NumericInput
                variant="standard"
                margin="normal"
                fullWidth
                name="price"
                label={t("productPrice")}
                error={touched.price && !!errors.price}
                helperText={(touched.price && errors.price) as string}
                onChange={(value) => setFieldValue("price", value)}
                value={values.price}
              />
            )}

            <TaxRateSelect
              name="tax"
              margin="normal"
              variant="standard"
              label={t("taxRate")}
              error={touched.tax_name && !!errors.tax_name}
              helperText={(touched.tax_name && errors.tax_name) as string}
              onChange={(value) => setFieldValue("tax_name", value)}
              value={values.tax_name}
            />

            {isSubmitting && <LinearProgress />}
            <Button type="submit" fullWidth variant="contained" color="primary" disabled={isSubmitting} sx={{ mt: 1 }}>
              {submitLabel}
            </Button>
          </Form>
        )}
      </Formik>
    </Paper>
  );
}
