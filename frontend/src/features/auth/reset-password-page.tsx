import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, Loader2 } from "lucide-react";
import { useState } from "react";
import { apiPost, getErrorMessage } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { AuthLayout } from "@/features/auth/auth-layout";

const schema = z
  .object({
    uid: z.string().min(1),
    token: z.string().min(1),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });

type FormValues = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const { error } = useToast();
  const [searchParams] = useSearchParams();
  const [done, setDone] = useState(false);
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { uid, token, password: "", confirm: "" },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      await apiPost("/auth/reset-password/", {
        uid: values.uid,
        token: values.token,
        password: values.password,
      });
      setDone(true);
    } catch (err) {
      error(getErrorMessage(err, "Unable to reset password. The link may be invalid or expired."));
    }
  };

  if (!uid || !token) {
    return (
      <AuthLayout>
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">Invalid or missing reset link.</p>
            <Link to="/forgot-password" className="text-primary mt-2 block text-sm hover:underline">
              Request a new link
            </Link>
          </CardContent>
        </Card>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <Card className="border-0 shadow-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl">Set a new password</CardTitle>
          <CardDescription>Choose a strong password for your account.</CardDescription>
        </CardHeader>
        <CardContent>
          {done ? (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <CheckCircle2 className="size-12 text-emerald-500" />
              <p className="font-medium">Password updated</p>
              <p className="text-muted-foreground text-sm">You can now sign in with your new password.</p>
              <Link to="/login" className="text-primary mt-2 text-sm hover:underline">
                Back to sign in
              </Link>
            </div>
          ) : (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>New password</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="confirm"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Confirm password</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
                  {form.formState.isSubmitting && <Loader2 className="animate-spin" />}
                  Reset password
                </Button>
              </form>
            </Form>
          )}
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
