import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Form, Formik, FormikHelpers } from "formik";
import { Avatar, Box, Button, Container, CssBaseline, LinearProgress, TextField, Typography } from "@mui/material";
import { z } from "zod";
import { selectIsAuthenticated, useAppSelector } from "@store";
import { LockOutlined as LockOutlinedIcon } from "@mui/icons-material";
import { useLoginMutation } from "@api/authApi";
import { toFormikValidationSchema } from "@stustapay/utils";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

const validationSchema = z.object({
  username: z.string(),
  password: z.string(),
});

type FormSchema = z.infer<typeof validationSchema>;

const initialValues: FormSchema = {
  username: "",
  password: "",
};

export const Login: React.FC = () => {
  const { t } = useTranslation(["auth", "common"]);
  const isLoggedIn = useAppSelector(selectIsAuthenticated);
  const [query] = useSearchParams();
  const navigate = useNavigate();
  const [login] = useLoginMutation();

  useEffect(() => {
    if (isLoggedIn) {
      const next = query.get("next");
      const redirectUrl = next != null ? next : "/";
      navigate(redirectUrl);
    }
  }, [isLoggedIn, navigate, query]);

  const handleSubmit = (values: FormSchema, { setSubmitting }: FormikHelpers<FormSchema>) => {
    setSubmitting(true);
    login({ username: values.username, password: values.password })
      .unwrap()
      .then(() => {
        setSubmitting(false);
      })
      .catch((err) => {
        setSubmitting(false);
        console.log(err);
        toast.error(t("loginFailed", { reason: err.error }));
      });
  };

  return (
    <Container component="main" maxWidth="xs">
      <CssBaseline />
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <Avatar sx={{ margin: 1, backgroundColor: "primary.main" }}>
          <LockOutlinedIcon />
        </Avatar>
        <Typography component="h1" variant="h5">
          Sign in
        </Typography>
        <Formik
          initialValues={initialValues}
          onSubmit={handleSubmit}
          validationSchema={toFormikValidationSchema(validationSchema)}
        >
          {({ values, handleBlur, handleChange, handleSubmit, isSubmitting }) => (
            <Form onSubmit={handleSubmit}>
              <input type="hidden" name="remember" value="true" />
              <TextField
                variant="outlined"
                margin="normal"
                required
                fullWidth
                autoFocus
                type="text"
                label={t("username")}
                name="username"
                onBlur={handleBlur}
                onChange={handleChange}
                value={values.username}
              />

              <TextField
                variant="outlined"
                margin="normal"
                required
                fullWidth
                type="password"
                name="password"
                label={t("password")}
                onBlur={handleBlur}
                onChange={handleChange}
                value={values.password}
              />

              {isSubmitting && <LinearProgress />}
              <Button
                type="submit"
                fullWidth
                variant="contained"
                color="primary"
                disabled={isSubmitting}
                sx={{ mt: 1 }}
              >
                {t("login")}
              </Button>
            </Form>
          )}
        </Formik>
      </Box>
    </Container>
  );
};
